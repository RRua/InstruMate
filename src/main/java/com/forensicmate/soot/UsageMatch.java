package com.forensicmate.soot;

import sootup.java.core.JavaSootMethod;

public class UsageMatch {
	
	private JavaSootMethod srcJavaSootMethod;
	private String trgClass;
	private String trgMethod;
	
	
	public UsageMatch() {
		
	}
	
	public UsageMatch(JavaSootMethod srcJavaSootMethod, String trgClass) {
		this(srcJavaSootMethod, trgClass, null);
	}
	
	public UsageMatch(JavaSootMethod srcJavaSootMethod, String trgClass, String trgMethod) {
		this.trgClass = trgClass;
		this.trgMethod = trgMethod;
	}
	
	public String getTrgClass() {
		return trgClass;
	}
	public void setTrgClass(String trgClass) {
		this.trgClass = trgClass;
	}
	public String getTrgMethod() {
		return trgMethod;
	}
	public void setTrgMethod(String trgMethod) {
		this.trgMethod = trgMethod;
	}
	public JavaSootMethod getSrcJavaSootMethod() {
		return srcJavaSootMethod;
	}
	public void setSrcJavaSootMethod(JavaSootMethod srcJavaSootMethod) {
		this.srcJavaSootMethod = srcJavaSootMethod;
	}

}
