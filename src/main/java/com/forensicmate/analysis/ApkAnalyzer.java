package com.forensicmate.analysis;

import java.io.File;
import java.util.Collection;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.forensicmate.AppContext;
import com.forensicmate.freemarker.FreemarkerModelFactory;
import com.forensicmate.freemarker.FreemarkerProcessor;
import com.forensicmate.soot.CSVLogger;
import com.forensicmate.soot.UsageMatch;
import com.forensicmate.soot.UsageService;

import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.java.bytecode.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.JavaProject;
import sootup.java.core.JavaSootClass;
import sootup.java.core.language.JavaLanguage;
import sootup.java.core.views.JavaView;

@Component
public class ApkAnalyzer {
	
	private static Logger LOG = LoggerFactory.getLogger(ApkAnalyzer.class);
	
	@Autowired
	private UsageService usageService;

	@Autowired
	private AppContext config;
	
	@Autowired
	private FreemarkerProcessor freemarkerProcessor;

	public void analyzeAll() {
		File inputApks = new File(config.getApkDir());
		listAPKFilesAndProcess(inputApks);
	}

	private void listAPKFilesAndProcess(File directory) {
		for (File file : directory.listFiles()) {
			if (file.isFile() && file.getName().endsWith(".apk")) {
				analyze(file);
			} else if (file.isDirectory()) {
				listAPKFilesAndProcess(file);
			}
		}
	}

	public void analyze(File apk) {
		AnalysisInputLocation<JavaSootClass> inputLocation = new JavaClassPathAnalysisInputLocation(
				apk.getAbsolutePath());
		JavaLanguage language = new JavaLanguage(8);
		JavaProject project = JavaProject.builder(language).addInputLocation(inputLocation).build();
		JavaView view = project.createView();
		Collection<JavaSootClass> classes = view.getClasses();
		CSVLogger csvLogger = new CSVLogger(apk, config.getOutputdir());
		LOG.info(String.format("Examining %s with %d classes", apk.getName(), classes.size()));
		List<UsageMatch> matches = new LinkedList<UsageMatch>();
		int processed = 0;
		for (JavaSootClass javaSootClass : classes) {
			usageService.findUsage(javaSootClass, csvLogger, matches);
			processed++;
			if(processed%(classes.size()*0.1)==0) {
				System.out.print("10% ");
			}
		}
		System.out.println();
		if(matches.size()>0) {
			LOG.info(String.format("Found %d match points", matches.size()));
			Map<String, Object> model = FreemarkerModelFactory.buildModelForMethods(matches);
			String outputDir = csvLogger.getAnalysisOutputDir();
			File outDirF = new File(outputDir);
			if(!outDirF.exists()) {
				outDirF.mkdir();
			}
			String name = "android_api_interceptor";
			String outputFile = name+".ts";
			String templateFile = name+ ".ftl";
	        freemarkerProcessor.produce(templateFile, new File(outputDir, outputFile), model);
		} else {
			LOG.info("Didn't find any api method");
		}
		csvLogger.finish();
	}

}
