package com.forensicmate.soot;

import java.util.Stack;

import sootup.core.jimple.visitor.TypeVisitor;
import sootup.core.types.ClassType;
import sootup.core.types.Type;

public class StackedTypeVisitor implements TypeVisitor, StackedVisitor {

	private Stack<String> visitedClasses = new Stack<String>();
	private boolean capturePrimitives = true;
	private boolean captureNonPrimitives = true;

	@Override
	public void caseBooleanType() {
		if (capturePrimitives)
			visitedClasses.push(Boolean.class.getName());
	}

	@Override
	public void caseByteType() {
		if (capturePrimitives)
			visitedClasses.push(Byte.class.getName());
	}

	@Override
	public void caseCharType() {
		if (capturePrimitives)
			visitedClasses.push(Character.class.getName());
	}

	@Override
	public void caseShortType() {
		if (capturePrimitives)
			visitedClasses.push(Short.class.getName());
	}

	@Override
	public void caseIntType() {
		if (capturePrimitives)
			visitedClasses.push(Integer.class.getName());
	}

	@Override
	public void caseLongType() {
		if (capturePrimitives)
			visitedClasses.push(Long.class.getName());
	}

	@Override
	public void caseDoubleType() {
		if (capturePrimitives)
			visitedClasses.push(Double.class.getName());
	}

	@Override
	public void caseFloatType() {
		if (capturePrimitives)
			visitedClasses.push(Float.class.getName());
	}

	@Override
	public void caseArrayType() {
		if (capturePrimitives)
			visitedClasses.push(ArrayType.class.getName());
	}

	@Override
	public void caseClassType(ClassType classType) {
		if (captureNonPrimitives)
			visitedClasses.push(classType.getFullyQualifiedName());
	}

	@Override
	public void caseNullType() {
		if (capturePrimitives)
			visitedClasses.push(NullType.class.getName());
	}

	@Override
	public void caseVoidType() {
		if (capturePrimitives)
			visitedClasses.push(Void.class.getName());
	}

	@Override
	public void caseUnknownType() {
		if (capturePrimitives)
			visitedClasses.push(UnknownType.class.getName());
	}

	@Override
	public void defaultCaseType() {
		if (capturePrimitives)
			visitedClasses.push(DefaultCaseType.class.getName());
	}

	public boolean isCapturePrimitives() {
		return capturePrimitives;
	}

	public void setCapturePrimitives(boolean capturePrimitives) {
		this.capturePrimitives = capturePrimitives;
	}

	public boolean isCaptureNonPrimitives() {
		return captureNonPrimitives;
	}

	public void setCaptureNonPrimitives(boolean captureNonPrimitives) {
		this.captureNonPrimitives = captureNonPrimitives;
	}

	public Stack<String> getVisitedClasses() {
		return visitedClasses;
	}

	public String getVisitedClass() {
		return visitedClasses.pop();
	}

	public String visitOnce(Type type) {
		int size = visitedClasses.size();
		type.accept(this);
		int newSize = visitedClasses.size();
		if (newSize - 1 == size) {
			return getVisitedClass();
		}
		return null;
	}

	public class ArrayType {

	}

	public class NullType {

	}

	public class UnknownType {

	}

	public class DefaultCaseType {

	}

	@Override
	public void reset() {
		this.visitedClasses.clear();
	}

}
