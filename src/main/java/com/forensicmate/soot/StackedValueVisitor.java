package com.forensicmate.soot;

import java.util.List;
import java.util.Stack;

import com.forensicmate.support.Utils;

import sootup.core.jimple.basic.Local;
import sootup.core.jimple.basic.Value;
import sootup.core.jimple.common.constant.BooleanConstant;
import sootup.core.jimple.common.constant.ClassConstant;
import sootup.core.jimple.common.constant.Constant;
import sootup.core.jimple.common.constant.DoubleConstant;
import sootup.core.jimple.common.constant.EnumConstant;
import sootup.core.jimple.common.constant.FloatConstant;
import sootup.core.jimple.common.constant.IntConstant;
import sootup.core.jimple.common.constant.LongConstant;
import sootup.core.jimple.common.constant.MethodHandle;
import sootup.core.jimple.common.constant.MethodType;
import sootup.core.jimple.common.constant.NullConstant;
import sootup.core.jimple.common.constant.StringConstant;
import sootup.core.jimple.common.expr.AbstractBinopExpr;
import sootup.core.jimple.common.expr.Expr;
import sootup.core.jimple.common.expr.JAddExpr;
import sootup.core.jimple.common.expr.JAndExpr;
import sootup.core.jimple.common.expr.JCastExpr;
import sootup.core.jimple.common.expr.JCmpExpr;
import sootup.core.jimple.common.expr.JCmpgExpr;
import sootup.core.jimple.common.expr.JCmplExpr;
import sootup.core.jimple.common.expr.JDivExpr;
import sootup.core.jimple.common.expr.JDynamicInvokeExpr;
import sootup.core.jimple.common.expr.JEqExpr;
import sootup.core.jimple.common.expr.JGeExpr;
import sootup.core.jimple.common.expr.JGtExpr;
import sootup.core.jimple.common.expr.JInstanceOfExpr;
import sootup.core.jimple.common.expr.JInterfaceInvokeExpr;
import sootup.core.jimple.common.expr.JLeExpr;
import sootup.core.jimple.common.expr.JLengthExpr;
import sootup.core.jimple.common.expr.JLtExpr;
import sootup.core.jimple.common.expr.JMulExpr;
import sootup.core.jimple.common.expr.JNeExpr;
import sootup.core.jimple.common.expr.JNegExpr;
import sootup.core.jimple.common.expr.JNewArrayExpr;
import sootup.core.jimple.common.expr.JNewExpr;
import sootup.core.jimple.common.expr.JNewMultiArrayExpr;
import sootup.core.jimple.common.expr.JOrExpr;
import sootup.core.jimple.common.expr.JPhiExpr;
import sootup.core.jimple.common.expr.JRemExpr;
import sootup.core.jimple.common.expr.JShlExpr;
import sootup.core.jimple.common.expr.JShrExpr;
import sootup.core.jimple.common.expr.JSpecialInvokeExpr;
import sootup.core.jimple.common.expr.JStaticInvokeExpr;
import sootup.core.jimple.common.expr.JSubExpr;
import sootup.core.jimple.common.expr.JUshrExpr;
import sootup.core.jimple.common.expr.JVirtualInvokeExpr;
import sootup.core.jimple.common.expr.JXorExpr;
import sootup.core.jimple.common.ref.JArrayRef;
import sootup.core.jimple.common.ref.JCaughtExceptionRef;
import sootup.core.jimple.common.ref.JFieldRef;
import sootup.core.jimple.common.ref.JInstanceFieldRef;
import sootup.core.jimple.common.ref.JParameterRef;
import sootup.core.jimple.common.ref.JStaticFieldRef;
import sootup.core.jimple.common.ref.JThisRef;
import sootup.core.jimple.common.ref.Ref;
import sootup.core.jimple.visitor.ExprVisitor;
import sootup.core.jimple.visitor.ValueVisitor;
import sootup.core.signatures.FieldSignature;
import sootup.core.signatures.MethodSignature;
import sootup.core.types.Type;

public class StackedValueVisitor implements ValueVisitor, ExprVisitor, StackedVisitor {

	private Stack<VisitedValue> visitedValues = new Stack<VisitedValue>();
	private StackedTypeVisitor typeVisitor;

	public StackedValueVisitor(StackedTypeVisitor typeVisitor) {
		this.typeVisitor = typeVisitor;
	}

	private void handleUses(List<Value> values) {
		for (Value value : values) {
			value.accept(this);
		}
	}

	private void handleExpr(Expr expr) {
		expr.getType().accept(this.typeVisitor);
		handleUses(expr.getUses());
	}

	private void handleBinaryExpr(AbstractBinopExpr expr) {
		expr.getOp1().accept(this);
		expr.getOp2().accept(this);
		expr.getOp1().getType().accept(this.typeVisitor);
		expr.getOp2().getType().accept(this.typeVisitor);
		handleExpr(expr);
	}

	private void handleField(JFieldRef ref) {
		ref.getType().accept(this.typeVisitor);
		handleUses(ref.getUses());
	}

	private void pushMethodSignature(MethodSignature methodSig) {
		String methodSignature = Utils.getJavaInvocationSignature(methodSig);
		visitedValues.push(new VisitedValue(methodSig.getDeclClassType(), methodSig.getName(), methodSig, true, methodSignature));
	}

	private void pushFieldSignature(FieldSignature fieldSig) {
		visitedValues.push(new VisitedValue(fieldSig.getDeclClassType(), fieldSig.getName(), fieldSig, false, null));
	}

	private void pushParameterRef(JParameterRef ref) {
		visitedValues.push(new VisitedValue(ref.getType(), null, ref, false, null));
	}

	@Override
	public void caseMethodHandle(MethodHandle handle) {
		String methodSignature = Utils.getJavaInvocationSignature(handle.getMethodSignature());
		visitedValues.push(new VisitedValue(handle.getType(), null, handle, true, methodSignature));
	}

	@Override
	public void caseMethodType(MethodType methodType) {
		visitedValues.push(new VisitedValue(methodType.getType(), null, methodType, false, null));
	}

	@Override
	public void caseLocal(Local local) {
		visitedValues.push(new VisitedValue(local.getType(), local.getName(), local, false, null));
	}

	@Override
	public void caseBooleanConstant(BooleanConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseDoubleConstant(DoubleConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseFloatConstant(FloatConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseIntConstant(IntConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseLongConstant(LongConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseNullConstant(NullConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseStringConstant(StringConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseEnumConstant(EnumConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseClassConstant(ClassConstant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void defaultCaseConstant(Constant constant) {
		visitedValues.push(new VisitedValue(constant.getType(), null, constant, false, null));
	}

	@Override
	public void caseAddExpr(JAddExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseAndExpr(JAndExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseCmpExpr(JCmpExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseCmpgExpr(JCmpgExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseCmplExpr(JCmplExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseDivExpr(JDivExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseEqExpr(JEqExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseNeExpr(JNeExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseGeExpr(JGeExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseGtExpr(JGtExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseLeExpr(JLeExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseLtExpr(JLtExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseMulExpr(JMulExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseOrExpr(JOrExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseRemExpr(JRemExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseShlExpr(JShlExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseShrExpr(JShrExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseUshrExpr(JUshrExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseSubExpr(JSubExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseXorExpr(JXorExpr expr) {
		handleBinaryExpr(expr);
	}

	@Override
	public void caseSpecialInvokeExpr(JSpecialInvokeExpr expr) {
		expr.getBase().accept(this);
		handleExpr(expr);
		pushMethodSignature(expr.getMethodSignature());
	}

	@Override
	public void caseVirtualInvokeExpr(JVirtualInvokeExpr expr) {
		expr.getBase().accept(this);
		handleExpr(expr);
		pushMethodSignature(expr.getMethodSignature());
	}

	@Override
	public void caseInterfaceInvokeExpr(JInterfaceInvokeExpr expr) {
		expr.getBase().accept(this);
		handleExpr(expr);
		pushMethodSignature(expr.getMethodSignature());
	}

	@Override
	public void caseStaticInvokeExpr(JStaticInvokeExpr expr) {
		handleExpr(expr);
		pushMethodSignature(expr.getMethodSignature());
	}

	@Override
	public void caseDynamicInvokeExpr(JDynamicInvokeExpr expr) {
		handleExpr(expr);
		pushMethodSignature(expr.getMethodSignature());
	}

	@Override
	public void caseCastExpr(JCastExpr expr) {
		expr.getOp().accept(this);
		handleExpr(expr);
	}

	@Override
	public void caseInstanceOfExpr(JInstanceOfExpr expr) {
		expr.getOp().accept(this);
		handleExpr(expr);
	}

	@Override
	public void caseNewArrayExpr(JNewArrayExpr expr) {
		expr.getBaseType().accept(this.typeVisitor);
		handleExpr(expr);
	}

	@Override
	public void caseNewMultiArrayExpr(JNewMultiArrayExpr expr) {
		expr.getBaseType().accept(this.typeVisitor);
		handleExpr(expr);
	}

	@Override
	public void caseNewExpr(JNewExpr expr) {
		handleExpr(expr);
	}

	@Override
	public void caseLengthExpr(JLengthExpr expr) {
		expr.getOp().accept(this);
		handleExpr(expr);
	}

	@Override
	public void caseNegExpr(JNegExpr expr) {
		expr.getOp().accept(this);
		handleExpr(expr);
	}

	@Override
	public void casePhiExpr(JPhiExpr v) {
		handleExpr(v);
	}

	@Override
	public void defaultCaseExpr(Expr expr) {
		handleExpr(expr);
	}

	@Override
	public void caseStaticFieldRef(JStaticFieldRef ref) {
		handleField(ref);
		pushFieldSignature(ref.getFieldSignature());
	}

	@Override
	public void caseInstanceFieldRef(JInstanceFieldRef ref) {
		handleField(ref);
		pushFieldSignature(ref.getFieldSignature());
	}

	@Override
	public void caseArrayRef(JArrayRef ref) {
		ref.getBase().accept(this);
		ref.getType().accept(this.typeVisitor);
		handleUses(ref.getUses());
	}

	@Override
	public void caseParameterRef(JParameterRef ref) {
		pushParameterRef(ref);
	}

	@Override
	public void caseCaughtExceptionRef(JCaughtExceptionRef ref) {
		ref.getType().accept(this.typeVisitor);
		handleUses(ref.getUses());
	}

	@Override
	public void caseThisRef(JThisRef ref) {
		ref.getType().accept(this.typeVisitor);
		handleUses(ref.getUses());
	}

	@Override
	public void defaultCaseRef(Ref ref) {
		ref.getType().accept(this.typeVisitor);
		handleUses(ref.getUses());
	}

	@Override
	public void defaultCaseValue(Value v) {
		v.getType().accept(this.typeVisitor);
		handleUses(v.getUses());
	}

	public Stack<VisitedValue> getVisitedValues() {
		return visitedValues;
	}

	public class VisitedValue {
		private String classType;
		private String name;
		private Object value;
		private boolean containsMethod;
		private String methodSignature;

		public VisitedValue(Type type, String name, Object value, boolean containsMethod, String methodSignature) {
			String visitedClass = StackedValueVisitor.this.typeVisitor.visitOnce(type);
			this.classType = visitedClass;
			this.name = name;
			this.value = value;
			this.containsMethod = containsMethod;
			this.methodSignature = methodSignature;
		}

		public String getClassType() {
			return classType;
		}

		public void setClassType(String classType) {
			this.classType = classType;
		}

		public String getName() {
			return name;
		}

		public void setName(String name) {
			this.name = name;
		}

		public Object getValue() {
			return value;
		}

		public void setValue(Object value) {
			this.value = value;
		}
		
		public boolean isContainsMethod() {
			return containsMethod;
		}

		public void setContainsMethod(boolean containsMethod) {
			this.containsMethod = containsMethod;
		}

		public String getMethodSignature() {
			return methodSignature;
		}

		public void setMethodSignature(String methodSignature) {
			this.methodSignature = methodSignature;
		}

		public String toString() {
			String val = this.value != null ? this.value.toString() : null;
			return String.format("Class: %s {name:%s, value:%s}", this.classType, this.name, val);
		}
	}

	@Override
	public void reset() {
		this.visitedValues.clear();
		this.typeVisitor.reset();
	}
}
