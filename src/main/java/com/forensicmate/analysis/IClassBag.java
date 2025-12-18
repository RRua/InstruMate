package com.forensicmate.analysis;

import java.util.List;

import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;

public interface IClassBag {

	public boolean isInBag(JavaSootClass clazz);
	
	public boolean isInBag(JavaSootClass clazz, JavaSootMethod method);
	
	public String getName();
	
	public List<String> getClazzes();
}
