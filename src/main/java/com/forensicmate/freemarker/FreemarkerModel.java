package com.forensicmate.freemarker;

import java.util.LinkedHashMap;

import com.forensicmate.support.Utils;

import sootup.core.types.ClassType;
import sootup.java.core.JavaSootMethod;

public class FreemarkerModel {
	private String clazz;
	private boolean enabled = true;
	private String signature;
	private String methodName;
	private String jsOverload;
	private String jsImplementation;
	private String jsArgsForCall;
	private String qualifier;
	private String reason;
	private LinkedHashMap<String, String> arguments = new LinkedHashMap<String, String>();
	private String returnType;
	
	
	public FreemarkerModel(JavaSootMethod method) {
		ClassType classType = method.getDeclaringClassType();
		String methodSignature = Utils.getMethodSignature(method);
		this.setClazz(classType.getFullyQualifiedName());
		this.setSignature(classType.getFullyQualifiedName()+"."+methodSignature);
		if (method.isConstructor()) {
			this.setMethodName("$init");
		} else {
			this.setMethodName(method.getName());
		}
		this.setJsOverload(Utils.getMethodSignatureForJavascriptOverload(method));
		this.setJsImplementation(Utils.getArgumentListForJavascriptImplementation(method));
		this.setJsArgsForCall(Utils.getArgumentListForActualImplementation(method));
		for (int i = 0; i < method.getParameterCount(); i++) {
			String argumentStr = "arg_"+i;
			arguments.put(argumentStr, method.getParameterType(i).toString());
		}
		this.returnType = method.getReturnType().toString();
	}

	public String getClazz() {
		return clazz;
	}

	public void setClazz(String clazz) {
		this.clazz = clazz;
	}

	public String getSignature() {
		return signature;
	}

	public void setSignature(String signature) {
		this.signature = signature;
	}

	public String getMethodName() {
		return methodName;
	}

	public void setMethodName(String methodName) {
		this.methodName = methodName;
	}

	public String getJsOverload() {
		return jsOverload;
	}

	public void setJsOverload(String jsOverload) {
		this.jsOverload = jsOverload;
	}

	public String getJsImplementation() {
		return jsImplementation;
	}

	public void setJsImplementation(String jsImplementation) {
		this.jsImplementation = jsImplementation;
	}

	public String getJsArgsForCall() {
		return jsArgsForCall;
	}

	public void setJsArgsForCall(String jsArgsForCall) {
		this.jsArgsForCall = jsArgsForCall;
	}

	public boolean isEnabled() {
		return enabled;
	}

	public void setEnabled(boolean enabled) {
		this.enabled = enabled;
	}

	public String getQualifier() {
		return qualifier;
	}

	public void setQualifier(String qualifier) {
		this.qualifier = qualifier;
	}

	public LinkedHashMap<String, String> getArguments() {
		return arguments;
	}

	public void setArguments(LinkedHashMap<String, String> arguments) {
		this.arguments = arguments;
	}

	public String getReturnType() {
		return returnType;
	}

	public void setReturnType(String returnType) {
		this.returnType = returnType;
	}

	public String getReason() {
		return reason;
	}

	public void setReason(String reason) {
		this.reason = reason;
	}

}
