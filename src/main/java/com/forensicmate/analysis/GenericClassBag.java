package com.forensicmate.analysis;

import java.util.LinkedList;
import java.util.List;

import sootup.core.types.Type;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;

public class GenericClassBag implements IClassBag {
	private String name;
	private List<String> clazzes = new LinkedList<String>();
	private List<String> returns = new LinkedList<String>();
	private List<String> arguments = new LinkedList<String>();
	private List<String> methodNames = new LinkedList<String>();
	private List<String> excludedMethodNames = new LinkedList<String>();
	private boolean allClassMethods = false;
	

	public GenericClassBag() {
		this.excludedMethodNames.add("equals");
		this.excludedMethodNames.add("hashCode");
		this.excludedMethodNames.add("toString");
		this.methodNames.add("<init>");
	}

	public GenericClassBag(String name, List<String> clazzes, List<String> returns, List<String> arguments,
			List<String> methodNames) {
		this.name = name;
		this.clazzes = clazzes;
		this.returns = returns;
		this.arguments = arguments;
		this.methodNames = methodNames;
	}

	public boolean isInBag(JavaSootClass clazz) {
		if (clazzes.contains(clazz.getType().getFullyQualifiedName())) {
			return true;
		} else {
			return false;
		}
	}

	public boolean isInBag(JavaSootClass clazz, JavaSootMethod method) {
		if (!isInBag(clazz)) {
			return false;
		}
		boolean selectedByReturn = false;
		boolean selectedByArgument = false;
		boolean selectedByName = false;
		boolean excludedByName = false;
		boolean isStaticInitializer = method.isStaticInitializer();

		Type returnType = method.getReturnType();
		if (this.returns.contains(returnType.toString())) {
			selectedByReturn = true;
		}

		List<Type> parameters = method.getParameterTypes();
		for (int i = 0; i < parameters.size(); i++) {
			if (this.arguments.contains(parameters.get(i).toString())) {
				selectedByArgument = true;
			}
		}

		if (this.methodNames.contains(method.getName())) {
			selectedByName = true;
		}
		
		if (this.excludedMethodNames.contains(method.getName())) {
			excludedByName = true;
		}

		if (!isStaticInitializer && !excludedByName) {
			if (selectedByArgument || selectedByReturn || selectedByName || this.allClassMethods) {
				return true;
			}
		}
		return false;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public List<String> getClazzes() {
		return clazzes;
	}

	public void setClazzes(List<String> clazzes) {
		this.clazzes = clazzes;
	}

	public List<String> getReturns() {
		return returns;
	}

	public void setReturns(List<String> returns) {
		this.returns = returns;
	}

	public List<String> getArguments() {
		return arguments;
	}

	public void setArguments(List<String> arguments) {
		this.arguments = arguments;
	}

	public List<String> getMethodNames() {
		return methodNames;
	}

	public void setMethodNames(List<String> methodNames) {
		this.methodNames = methodNames;
	}

	public boolean isAllClassMethods() {
		return allClassMethods;
	}

	public void setAllClassMethods(boolean allClassMethods) {
		this.allClassMethods = allClassMethods;
	}

	public List<String> getExcludedMethodNames() {
		return excludedMethodNames;
	}

	public void setExcludedMethodNames(List<String> exludedMethodNames) {
		this.excludedMethodNames = exludedMethodNames;
	}

}
