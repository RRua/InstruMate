package com.forensicmate.soot;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;

import com.forensicmate.support.StringUtils;

public class CSVLogger {

	public static String IGNORED_CLASSES = "IGNORED_CLASSES";
	public static String[] IGNORED_CLASSES_CLMNS = new String[] { "class_name", "reason" };
	public static String INSPECTED_CLASSES = "INSPECTED_CLASSES";
	public static String[] INSPECTED_CLASSES_CLMNS = new String[] { "class_name", "method", "success", "failure",
			"qtd_matches" };
	
	public static String METHOD_USAGE_POINTS = "METHOD_USAGE_POINTS";
	public static String[] METHOD_USAGE_POINTS_CLMNS = new String[] { "src_class", "src_method", "target_method", "stmt_str" };
	
	public static String CLASS_USAGE_POINTS = "CLASS_USAGE_POINTS";
	public static String[] CLASS_USAGE_POINTS_CLMNS = new String[] { "src_class", "src_method", "target_class", "stmt_str" };
	
	private Map<String, CSVPrinter> csvPrinters = new LinkedHashMap<>();
	private String outdir;

	public CSVLogger(File apk, String baseOutputDir) {
		String apkName = StringUtils.extractFileNameWithoutExtension(apk);
		//SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd-HH-mm");
		//String dateStr = dateFormat.format(new Date());
		//this.outdir = baseOutputDir + "/" +apkName+"-"+ dateStr + "/";
		this.outdir = baseOutputDir + "/" +apkName+"/";
		this.registerAnalysis(IGNORED_CLASSES, IGNORED_CLASSES_CLMNS);
		this.registerAnalysis(INSPECTED_CLASSES, INSPECTED_CLASSES_CLMNS);
		this.registerAnalysis(CLASS_USAGE_POINTS, CLASS_USAGE_POINTS_CLMNS);
		this.registerAnalysis(METHOD_USAGE_POINTS, METHOD_USAGE_POINTS_CLMNS);
	}

	public void registerAnalysis(String name, String[] columns) {
		if (!containsAnalysis(name)) {
			try {
				CSVFormat csvFormat = CSVFormat.Builder.create().setHeader(columns).setAllowMissingColumnNames(false)
						.build();
				File outdir = new File(this.outdir);
				outdir.mkdir();
				File file = getAnalysisFile(name);
				FileWriter fileWriter = new FileWriter(file);
				CSVPrinter csvPrinter = new CSVPrinter(fileWriter, csvFormat);
				csvPrinters.put(name, csvPrinter);
			} catch (IOException e) {
				throw new RuntimeException(e);
			}
		}
	}
	
	public String getAnalysisOutputDir() {
		return this.outdir;
	}
	
	public File getAnalysisFile(String name) {
		return new File(this.outdir, name+".csv");
	}

	public void logAnalysisItem(String name, String[] rows) {
		CSVPrinter csvPrinter = csvPrinters.get(name);
		if (csvPrinter != null) {
			try {
				csvPrinter.printRecord((Object[]) rows);
			} catch (IOException e) {
				throw new RuntimeException(e);
			}
		} else {
			throw new IllegalStateException("CSV Printer not found for analysis: " + name);
		}
	}

	public void finish() {
		for (CSVPrinter csvPrinter : csvPrinters.values()) {
			try {
				csvPrinter.close();
			} catch (IOException e) {
				throw new RuntimeException(e);
			}
		}
	}

	public boolean containsAnalysis(String name) {
		return csvPrinters.get(name) != null;
	}

}
