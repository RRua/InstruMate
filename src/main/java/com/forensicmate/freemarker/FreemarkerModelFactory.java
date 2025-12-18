package com.forensicmate.freemarker;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.forensicmate.soot.UsageMatch;
import com.forensicmate.support.Utils;

import sootup.java.core.JavaSootMethod;

public class FreemarkerModelFactory {

	public static Map<String, Object> buildModelForMethods(List<JavaSootMethod> methods,
			Map<String, Set<String>> qualifiers) {
		Set<String> visitedMethods = new LinkedHashSet<String>();
		List<FreemarkerModel> models = new LinkedList<FreemarkerModel>();
		for (JavaSootMethod method : methods) {
			String signature = Utils.getJavaInvocationSignature(method.getSignature());
			if (!visitedMethods.contains(signature)) {
				visitedMethods.add(signature);
				FreemarkerModel model = new FreemarkerModel(method);
				Set<String> mqualifiers = qualifiers.get(signature);
				if (mqualifiers != null) {
					model.setQualifier(String.join("|", mqualifiers));
				}
				model.setReason("API");
				models.add(model);
			}
		}
		Map<String, Object> res = new LinkedHashMap<String, Object>();
		res.put("items", models);
		return res;
	}

	public static Map<String, Object> buildModelForMethods(List<UsageMatch> matches) {
		Set<String> visitedMethods = new LinkedHashSet<String>();
		List<FreemarkerModel> models = new LinkedList<FreemarkerModel>();
		for (UsageMatch usageMatch : matches) {
			JavaSootMethod method = usageMatch.getSrcJavaSootMethod();
			String signature = Utils.getJavaInvocationSignature(method.getSignature());
			if (!visitedMethods.contains(signature)) {
				visitedMethods.add(signature);
				FreemarkerModel model = new FreemarkerModel(method);
				model.setReason(String.format("trgClass: %s trgMethod: %s",usageMatch.getTrgClass(),usageMatch.getTrgMethod()));
				model.setQualifier("APPLICATION");
				models.add(model);
			}
		}
		Map<String, Object> res = new LinkedHashMap<String, Object>();
		res.put("items", models);
		return res;
	}

}
