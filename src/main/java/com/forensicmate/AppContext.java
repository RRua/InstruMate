package com.forensicmate;

import java.io.File;

import com.forensicmate.support.Utils;

public class AppContext {
	
	private String inputdir;
	private String outputdir;
	private String tmpDir;

	public AppContext(String inputdir, String outputdir, String tmpDir) {
		this.inputdir = inputdir;
		this.outputdir = outputdir;
		this.tmpDir = tmpDir;
		Utils.deleteDirectoryContents(new File(this.outputdir));
	}
	
	public String getApiDir() {
		return this.inputdir+"/api-jar";
	}
	
	public String getApkDir() {
		return this.inputdir+"/apk";
	}
	
	public String getTemplatesDir() {
		return this.inputdir+"/templates";
	}
	
	public String getConfigDir() {
		return this.inputdir+"/config";
	}
	
	public String getOutputOfApiInterceptors() {
		return this.outputdir+"/api-interceptors";
	}
	
	public String getInputdir() {
		return inputdir;
	}


	public void setInputdir(String inputdir) {
		this.inputdir = inputdir;
	}


	public String getOutputdir() {
		return outputdir;
	}

	public void setOutputdir(String outputdir) {
		this.outputdir = outputdir;
	}

	public String getTmpDir() {
		return tmpDir;
	}

	public void setTmpDir(String tmpDir) {
		this.tmpDir = tmpDir;
	}

}
