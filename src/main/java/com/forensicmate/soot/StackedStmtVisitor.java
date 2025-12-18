package com.forensicmate.soot;

import java.util.LinkedList;
import java.util.List;
import java.util.Stack;

import sootup.core.jimple.basic.Value;
import sootup.core.jimple.common.stmt.BranchingStmt;
import sootup.core.jimple.common.stmt.JAssignStmt;
import sootup.core.jimple.common.stmt.JGotoStmt;
import sootup.core.jimple.common.stmt.JIdentityStmt;
import sootup.core.jimple.common.stmt.JIfStmt;
import sootup.core.jimple.common.stmt.JInvokeStmt;
import sootup.core.jimple.common.stmt.JNopStmt;
import sootup.core.jimple.common.stmt.JReturnStmt;
import sootup.core.jimple.common.stmt.JReturnVoidStmt;
import sootup.core.jimple.common.stmt.JThrowStmt;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.jimple.javabytecode.stmt.JBreakpointStmt;
import sootup.core.jimple.javabytecode.stmt.JEnterMonitorStmt;
import sootup.core.jimple.javabytecode.stmt.JExitMonitorStmt;
import sootup.core.jimple.javabytecode.stmt.JRetStmt;
import sootup.core.jimple.javabytecode.stmt.JSwitchStmt;
import sootup.core.jimple.visitor.StmtVisitor;
import sootup.core.model.Body;
import sootup.core.model.SootMethod;

public class StackedStmtVisitor implements StmtVisitor, StackedVisitor {

	private StackedTypeVisitor typeVisitor;
	private StackedValueVisitor valueVisitor;
	private boolean followBranches = true;
	private boolean checkUsages = false;
	private boolean checkDefinitions = false;
	private Body body;

	enum ValueTypes {
		USAGE, DEFINITION
	}

	public StackedStmtVisitor() {
		this.typeVisitor = new StackedTypeVisitor();
		this.valueVisitor = new StackedValueVisitor(typeVisitor);
	}

	public void configure(SootMethod method) {
		this.body = method.getBody();
	}

	public List<String> getVisitedClasses() {
		Stack<String> visitedClasses = this.typeVisitor.getVisitedClasses();
		List<String> list = new LinkedList<String>();
		list.addAll(visitedClasses);
		return list;
	}

	public List<String> getVisitedMethods() {
		List<String> methodSignatures = new LinkedList<String>();
		List<StackedValueVisitor.VisitedValue> visitedValues = this.valueVisitor.getVisitedValues();
		for (StackedValueVisitor.VisitedValue visitedValue : visitedValues) {
			if(visitedValue.isContainsMethod()) {
				methodSignatures.add(visitedValue.getMethodSignature());
			}
		}
		return methodSignatures;
	}

	private void handleValues(List<Value> values, ValueTypes vType) {
		switch (vType) {
		case USAGE:
			if (this.checkUsages)
				for (Value value : values) {
					value.accept(this.valueVisitor);
				}
			break;
		case DEFINITION:
			if (this.checkDefinitions)
				for (Value value : values) {
					value.accept(this.valueVisitor);
				}
			break;
		}
	}

	private void handleStmt(Stmt stmt) {
		// references an array?
		if (stmt.containsArrayRef()) {
			stmt.getArrayRef().accept(this.valueVisitor);
		}
		handleValues(stmt.getUses(), ValueTypes.USAGE);
		handleValues(stmt.getDefs(), ValueTypes.DEFINITION);

		// references a field?
		if (stmt.containsFieldRef()) {
			stmt.getFieldRef().accept(this.valueVisitor);
		}
		if (stmt.containsInvokeExpr()) {
			stmt.getInvokeExpr().accept(this.valueVisitor);
		}
	}

	private void handleBranchingStmt(BranchingStmt stmt) {
		if (this.followBranches) {
			List<Stmt> stmts = stmt.getTargetStmts(this.body);
			for (Stmt stmt2 : stmts) {
				stmt2.accept(this);
			}
		}
		handleStmt(stmt);
	}

	@Override
	public void caseBreakpointStmt(JBreakpointStmt stmt) {
	}

	@Override
	public void caseInvokeStmt(JInvokeStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseAssignStmt(JAssignStmt<?, ?> stmt) {
		handleStmt(stmt);
		stmt.getLeftOp().accept(this.valueVisitor);
		stmt.getRightOp().accept(this.valueVisitor);
	}

	@Override
	public void caseIdentityStmt(JIdentityStmt<?> stmt) {
		handleStmt(stmt);
		stmt.getLeftOp().accept(this.valueVisitor);
		stmt.getRightOp().accept(this.valueVisitor);
	}

	@Override
	public void caseEnterMonitorStmt(JEnterMonitorStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseExitMonitorStmt(JExitMonitorStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseGotoStmt(JGotoStmt stmt) {
		handleBranchingStmt(stmt);
	}

	@Override
	public void caseIfStmt(JIfStmt stmt) {
		handleBranchingStmt(stmt);
	}

	@Override
	public void caseNopStmt(JNopStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseRetStmt(JRetStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseReturnStmt(JReturnStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseReturnVoidStmt(JReturnVoidStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void caseSwitchStmt(JSwitchStmt stmt) {
		handleBranchingStmt(stmt);
	}

	@Override
	public void caseThrowStmt(JThrowStmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void defaultCaseStmt(Stmt stmt) {
		handleStmt(stmt);
	}

	@Override
	public void reset() {
		this.typeVisitor.reset();
		this.valueVisitor.reset();
	}

}
