package com.forensicmate.analysis;

import java.io.File;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.forensicmate.AppContext;
import com.forensicmate.freemarker.FreemarkerModelFactory;
import com.forensicmate.freemarker.FreemarkerProcessor;
import com.forensicmate.support.Utils;

import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.java.bytecode.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.JavaProject;
import sootup.java.core.JavaProject.JavaProjectBuilder;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.language.JavaLanguage;
import sootup.java.core.views.JavaView;

@Component
public class ApiAnalyzer {

	private static Logger LOG = LoggerFactory.getLogger(ApiAnalyzer.class);

	@Autowired
	private AppContext config;

	@Autowired
	private FreemarkerProcessor freemarkerProcessor;

	public void analyzeAll() {
		File inputDir = new File(config.getApiDir());
		listApiFilesAndProcess(inputDir);
	}

	private void listApiFilesAndProcess(File directory) {
		JavaLanguage language = new JavaLanguage(8);
		JavaProjectBuilder projectBuilder = JavaProject.builder(language);
		for (File file : directory.listFiles()) {
			if (file.isFile() && (file.getName().endsWith(".jar") || file.getName().endsWith(".aar"))) {
				AnalysisInputLocation<JavaSootClass> inputLocation = new JavaClassPathAnalysisInputLocation(
						file.getAbsolutePath());
				projectBuilder.addInputLocation(inputLocation);
			} else if (file.isDirectory()) {
				listApiFilesAndProcess(file);
			}
		}

		JavaProject project = projectBuilder.build();
		JavaView view = project.createView();
		analyze(view.getClasses());
	}

	private void analyze(Collection<JavaSootClass> classes) {
		List<JavaSootMethod> allApiMethods = new LinkedList<JavaSootMethod>();
		List<IClassBag> apis = ClassBagBuilder.getApis();
		Map<String, Set<String>> qualifiers = new LinkedHashMap<String, Set<String>>();
		for (JavaSootClass javaSootClass : classes) {
			for (IClassBag apiBag : apis) {
				if (apiBag.isInBag(javaSootClass)) {
					Set<? extends JavaSootMethod> methods = null;
					try {
						methods = javaSootClass.getMethods();
					} catch (Throwable t) {
						LOG.info(String.format("Soot error at class %s error %s", javaSootClass.getName(),
								t.getMessage()));
						LOG.error(t.getMessage());
						t.printStackTrace();
					}
					if (methods != null) {
						for (JavaSootMethod method : methods) {
							if (apiBag.isInBag(javaSootClass, method)) {
								allApiMethods.add(method);
								String signature = Utils.getJavaInvocationSignature(method.getSignature());
								Set<String> methodQualifiers = qualifiers.get(signature);
								if (methodQualifiers == null) {
									methodQualifiers = new LinkedHashSet<String>();
									qualifiers.put(signature, methodQualifiers);
								}
								methodQualifiers.add(apiBag.getName());
							}
						}
					}
				}
			}
		}
		if (allApiMethods.size() > 0) {
			Map<String, Object> model = FreemarkerModelFactory.buildModelForMethods(allApiMethods, qualifiers);
			String outputDir = config.getOutputOfApiInterceptors();
			File outDirF = new File(outputDir);
			if (!outDirF.exists()) {
				outDirF.mkdir();
			}
			String name = "android_api_interceptor";
			String outputFile = name + ".ts";
			String templateFile = name + ".ftl";
			freemarkerProcessor.produce(templateFile, new File(outputDir, outputFile), model);
			LOG.info(String.format("Created interceptors for %d API points", allApiMethods.size()));
		} else {
			LOG.info("Didn't find any api method");
		}

	}

}
