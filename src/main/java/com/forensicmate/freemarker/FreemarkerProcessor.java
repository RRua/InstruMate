package com.forensicmate.freemarker;

import java.io.File;
import java.io.FileWriter;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.ui.freemarker.FreeMarkerTemplateUtils;

import freemarker.template.Configuration;
import freemarker.template.Template;

@Component
public class FreemarkerProcessor {

	private static Logger LOG = LoggerFactory.getLogger(FreemarkerProcessor.class);

	@Autowired
	private Configuration freemarkerConfig;

	public void produce(String templateFile, File output, Map<String, Object> model) {
		try {
			Template template = freemarkerConfig.getTemplate(templateFile);
			String processedTemplate = FreeMarkerTemplateUtils.processTemplateIntoString(template, model);
			try (FileWriter fileWriter = new FileWriter(output)) {
				fileWriter.write(processedTemplate);
			}
			LOG.info("Template processed and written to: " + output.getAbsolutePath());
		} catch (Exception e) {
			throw new RuntimeException(e);
		}
	}

}
