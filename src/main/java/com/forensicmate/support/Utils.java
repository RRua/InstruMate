package com.forensicmate.support;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.LinkedList;
import java.util.List;

import com.forensicmate.soot.StackedTypeVisitor;
import com.forensicmate.soot.StackedTypeVisitor.ArrayType;

import sootup.core.signatures.MethodSignature;
import sootup.core.types.ClassType;
import sootup.core.types.Type;
import sootup.java.core.JavaSootMethod;

public class Utils {

	public static String getJavaInvocationSignature(MethodSignature methodSignature) {
		StringBuilder out = new StringBuilder();
		ClassType classType = methodSignature.getDeclClassType();
		methodSignature.getParameterTypes();
		out.append(classType.getFullyQualifiedName()).append(".").append(methodSignature.getName());
		List<Type> parameters = methodSignature.getParameterTypes();
		int i = 0;
		out.append("(");
		for (Type type : parameters) {
			if (i > 0) {
				out.append(",");
			}
			out.append(type.toString());
			i++;
		}
		out.append(")");
		return out.toString();
	}

	public static String getMethodSignatureForJavascriptOverload(JavaSootMethod method) {
		StringBuilder signature = new StringBuilder();
		List<Type> parameterTypes = method.getParameterTypes();
		for (int i = 0; i < parameterTypes.size(); i++) {
			if (i > 0) {
				signature.append(",");
			}
			boolean isArray = false;

			Type parameterType = parameterTypes.get(i);
			StackedTypeVisitor visitor = new StackedTypeVisitor();
			String visitedType = visitor.visitOnce(parameterType);
			if (ArrayType.class.getName().equals(visitedType)) {
				isArray = true;
			}
			String parameterSpec = null;
			if (!isArray) {
				parameterSpec = parameterType.toString();
			} else {
				// convert java.lang.Object[] to [Ljava.lang.Object;
				// convert float[] => [F
				// convert byte[] => '[B'
				String tmpStr = parameterType.toString();
				tmpStr = tmpStr.substring(0, tmpStr.indexOf('['));
				if ("float".equals(tmpStr)) {
					parameterSpec = "[F";
				} else if ("byte".equals(tmpStr)) {
					parameterSpec = "[B";
				} else if ("double".equals(tmpStr)) {
					parameterSpec = "[D";
				} else if ("int".equals(tmpStr)) {
					parameterSpec = "[I";
				} else if("char".equals(tmpStr)) {
					parameterSpec = "[C";
				} else if("long".equals(tmpStr)) { 
					parameterSpec = "[J";
				}else if("boolean".equals(tmpStr)) { 
					parameterSpec = "[Z";
				}else if("short".equals(tmpStr)) {
					parameterSpec = "[S";
				} else {
					parameterSpec = String.format("[L%s;", tmpStr);
				}
			}
			signature.append(String.format("'%s'", parameterSpec));
		}
		return signature.toString();
	}

	public static String getArgumentListForJavascriptImplementation(JavaSootMethod method) {
		StringBuilder arguments = new StringBuilder();
		for (int i = 0; i < method.getParameterCount(); i++) {
			if (i > 0) {
				arguments.append(", ");
			}
			String argumentStr = "arg_" + i;
			arguments.append(String.format("%s:any", argumentStr));
		}
		return arguments.toString();
	}

	public static String getArgumentListForActualImplementation(JavaSootMethod method) {
		StringBuilder arguments = new StringBuilder();
		for (int i = 0; i < method.getParameterCount(); i++) {
			if (i > 0) {
				arguments.append(", ");
			}
			String argumentStr = "arg_" + i;
			arguments.append(String.format("%s", argumentStr));
		}
		return arguments.toString();
	}

	public static String getMethodSignature(JavaSootMethod method) {
		StringBuilder out = new StringBuilder(method.getName());
		List<Type> parameters = method.getParameterTypes();
		int i = 0;
		out.append("(");
		for (Type type : parameters) {
			if (i > 0) {
				out.append(",");
			}
			out.append(type.toString());
			i++;
		}
		out.append(")");
		return out.toString();
	}

	public static void copyFolder(File source, File destination) throws IOException {
		if (!source.isDirectory()) {
			throw new IllegalArgumentException("Source must be a directory");
		}
		if (!destination.isDirectory()) {
			throw new IllegalArgumentException("Destination must be a directory");
		}

		for (File file : source.listFiles()) {
			if (file.isDirectory()) {
				copyFolder(file, new File(destination, file.getName()));
			} else {
				Files.copy(Paths.get(file.getPath()), Paths.get(destination.getPath(), file.getName()));
			}
		}
	}

	public static void deleteDirectoryContents(File directory) {
		if (!directory.exists()) {
			return;
		}
		for (File file : directory.listFiles()) {
			if (file.isDirectory()) {
				deleteDirectoryContents(file);
			} else {
				file.delete();
			}
		}
	}

	public static List<String> readStringsFromFile(String dir, String file) {
		List<String> res = new LinkedList<>();
		try {
			BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(new File(dir, file))));
			String line;
			while ((line = reader.readLine()) != null) {
				res.add(line);
			}
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
		return res;
	}
}
