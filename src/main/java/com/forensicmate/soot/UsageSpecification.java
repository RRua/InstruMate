package com.forensicmate.soot;

import java.util.List;

import sootup.java.core.JavaSootMethod;

public interface UsageSpecification {
	
	public int matches(JavaSootMethod method, List<UsageMatch> allMatches);
	
}
