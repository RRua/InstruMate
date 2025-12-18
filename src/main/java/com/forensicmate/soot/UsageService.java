package com.forensicmate.soot;

import static com.forensicmate.soot.CSVLogger.IGNORED_CLASSES;
import static com.forensicmate.soot.CSVLogger.INSPECTED_CLASSES;

import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import javax.annotation.PostConstruct;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.forensicmate.AppContext;
import com.forensicmate.analysis.ClassBagBuilder;
import com.forensicmate.analysis.GenericClassBag;
import com.forensicmate.analysis.IClassBag;
import com.forensicmate.support.Utils;

import sootup.core.signatures.PackageName;
import sootup.core.types.ClassType;
import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;

@Component
public class UsageService {

	private static Logger LOG = LoggerFactory.getLogger(UsageService.class);
	private List<String> androidPackages;
	private List<UsageSpecification> usageSpecifications = new LinkedList<UsageSpecification>();

	@Autowired
	private AppContext appContext;

	@PostConstruct
	public void afterPropertiesSet() {
		androidPackages = Utils.readStringsFromFile(appContext.getConfigDir(), "ignored-packages.lst");
		List<IClassBag> bags = ClassBagBuilder.getApis();
		Set<String> apiClasses = new TreeSet<String>();
		for (IClassBag iClassBag : bags) {
			if(iClassBag instanceof GenericClassBag) {
				apiClasses.addAll(iClassBag.getClazzes());
			}
		}
		GenericUsageSpecification usageSpecification = new GenericUsageSpecification(new TreeSet<String>(), apiClasses);
		this.usageSpecifications.add(usageSpecification);
	}

	public int findUsage(JavaSootClass jSClass, CSVLogger csvLogger, List<UsageMatch> matches) {
		ClassType classType = jSClass.getType();
		PackageName packageName = classType.getPackageName();
		String className = jSClass.getName();
		String strPkgName = packageName.getPackageName();

		for (String androidPackage : androidPackages) {
			if (strPkgName.equals(androidPackage) || strPkgName.startsWith(androidPackage + ".")) {
				csvLogger.logAnalysisItem(IGNORED_CLASSES, new String[] { className });
				return 0;
			}
		}
		int qtdMatches = 0;
		// if (className.contains("SensitiveApisFragment")) {
		try {
			Set<? extends JavaSootMethod> methods = jSClass.getMethods();
			for (JavaSootMethod method : methods) {
				qtdMatches += findUsagesInMethodBody(method, csvLogger, matches);
			}
		} catch (Throwable t) {
			csvLogger.logAnalysisItem(INSPECTED_CLASSES, new String[] { className, "", "0", "999" });
		}
		// }
		return qtdMatches;
	}

	private int findUsagesInMethodBody(JavaSootMethod method, CSVLogger results, List<UsageMatch> allMatches) {
		String className = method.getDeclaringClassType().getFullyQualifiedName();
		String methodName = Utils.getMethodSignature(method);
		LOG.debug(methodName);
		int qtdMatches = 0;
		try {
			for (UsageSpecification spec : this.usageSpecifications) {
				qtdMatches += spec.matches(method, allMatches);
			}
			results.logAnalysisItem(INSPECTED_CLASSES,
					new String[] { className, methodName, "1", "0", Integer.valueOf(qtdMatches).toString() });
		} catch (Throwable t) {
			results.logAnalysisItem(INSPECTED_CLASSES,
					new String[] { className, methodName, "0", "1", Integer.valueOf(qtdMatches).toString() });
		}
		return qtdMatches;
	}

}
