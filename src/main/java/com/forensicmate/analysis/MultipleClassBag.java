package com.forensicmate.analysis;

import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import sootup.java.core.JavaSootClass;
import sootup.java.core.JavaSootMethod;

public class MultipleClassBag implements IClassBag {
	
	private List<IClassBag> bags = new LinkedList<IClassBag>();
	private String name;
	
	public MultipleClassBag(String name, IClassBag... bag) {
		this.name = name;
		for (int i = 0; i < bag.length; i++) {
			bags.add(bag[i]);
		}
	}

	@Override
	public boolean isInBag(JavaSootClass clazz) {
		for (IClassBag iClassBag : bags) {
			if(iClassBag.isInBag(clazz)) {
				return true;
			}
		}
		return false;
	}

	@Override
	public boolean isInBag(JavaSootClass clazz, JavaSootMethod method) {
		for (IClassBag iClassBag : bags) {
			if(iClassBag.isInBag(clazz, method)) {
				return true;
			}
		}
		return false;
	}

	@Override
	public String getName() {
		return name;
	}

	@Override
	public List<String> getClazzes() {
		Set<String> clazzes = new TreeSet<String>();
		for (IClassBag iClassBag : bags) {
			clazzes.addAll(iClassBag.getClazzes());
		}
		List<String> res = new LinkedList<String>();
		res.addAll(clazzes);
		return res;
	}

}
