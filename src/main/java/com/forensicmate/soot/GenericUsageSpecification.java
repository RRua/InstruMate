package com.forensicmate.soot;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.forensicmate.support.Utils;

import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.Body;
import sootup.java.core.JavaSootMethod;

public class GenericUsageSpecification implements UsageSpecification {
	
	private static Logger LOG = LoggerFactory.getLogger(GenericUsageSpecification.class);
	private Set<String> methodSignatures;
	private Set<String> classNames;
	
	public GenericUsageSpecification(Set<String> methodSignatures, Set<String> classNames) {
		this.methodSignatures = methodSignatures;
		this.classNames = classNames;
	}
	
	@Override
	public int matches(JavaSootMethod method, List<UsageMatch> res) {
		int qtdMatches = 0;
		String methodName = Utils.getMethodSignature(method);
		LOG.debug(methodName);
		if (method.hasBody()) {
			Body body = method.getBody();
			List<Stmt> stmts = body.getStmts();
			StackedStmtVisitor stmtVisitor = new StackedStmtVisitor();
			stmtVisitor.configure(method);
			for (Stmt stmt : stmts) {
				LOG.debug(stmt.toString());
				stmtVisitor.reset();
				stmt.accept(stmtVisitor);
				List<String> visitedClasses = stmtVisitor.getVisitedClasses();
				List<String> visitedMethods = stmtVisitor.getVisitedMethods();
				String matchedTrgClass = this.matchesAnyClass(visitedClasses);
				String matchedTrgMethod = this.matchesAnyMethod(visitedMethods);
				
				if(matchedTrgClass!=null || matchedTrgMethod!=null) {
					UsageMatch match = new UsageMatch();
					match.setSrcJavaSootMethod(method);
					match.setTrgClass(matchedTrgClass);
					match.setTrgMethod(matchedTrgMethod);
					res.add(match);
					qtdMatches++;
				}
			}
		}
		return qtdMatches;
	}
	
	private String matchesAnyClass(List<String> visitedClasses) {
		Set<String> matchStrings = new TreeSet<String>();
		int qtdMatches = 0;
		for (String visitedClass : visitedClasses) {
			if (this.classNames.contains(visitedClass)) {
				matchStrings.add(visitedClass);
				qtdMatches++;
			}
		}
		if(qtdMatches>0) {
			return String.join("|", matchStrings);
		}
		return null;
	}
	
	private String matchesAnyMethod(List<String> visitedMethods) {
		Set<String> matchStrings = new TreeSet<String>();
		int qtdMatches = 0;
		for (String visitedMethod : visitedMethods) {
			if (this.methodSignatures.contains(visitedMethod)) {
				matchStrings.add(visitedMethod);
				qtdMatches++;
			}
		}
		if(qtdMatches>0) {
			return String.join("|", matchStrings);
		}
		return null;
	}

}
