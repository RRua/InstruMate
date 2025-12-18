package com.forensicmate;

import java.io.File;
import java.io.IOException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.ui.freemarker.FreeMarkerConfigurationFactoryBean;

import com.forensicmate.analysis.ApiAnalyzer;
import com.forensicmate.analysis.ApkAnalyzer;

import freemarker.template.Configuration;
import freemarker.template.TemplateException;

@SpringBootApplication
@ComponentScan
public class Application implements ApplicationRunner {
	private static Logger LOG = LoggerFactory.getLogger(Application.class);
	
	@Autowired
	private ApiAnalyzer apiAnalyzer;
	
	@Autowired
	private ApkAnalyzer apkAnalyzer;
	
	public static void main(String[] args) {
		LOG.info("STARTING THE APPLICATION");
		SpringApplication.run(Application.class, args);
		LOG.info("APPLICATION FINISHED");
	}

	@Override
	public void run(ApplicationArguments args) throws Exception {
		apiAnalyzer.analyzeAll();
		//apkAnalyzer.analyzeAll();
	}
	
	@Bean
	public AppContext applicationConfiguration() {
		String inputDir = "./input";
		String outputDir = "./output";
		String tmpDir = "./tmp";
		File outputDirFile = new File(outputDir);
		if (!outputDirFile.exists()) {
			outputDirFile.mkdir();
		}
		AppContext config = new AppContext(inputDir, outputDir, tmpDir);
		return config;
	}

	@Bean
	public Configuration freemarkerConfig() throws IOException, TemplateException {
		FreeMarkerConfigurationFactoryBean factory = new FreeMarkerConfigurationFactoryBean();
		factory.setTemplateLoaderPath("file:" + applicationConfiguration().getTemplatesDir());
		factory.setPreferFileSystemAccess(true);
		factory.afterPropertiesSet();
		Configuration cfg = factory.getObject();
		return cfg;
	}

}
