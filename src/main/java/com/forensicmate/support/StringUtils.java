package com.forensicmate.support;

import java.io.File;
import java.nio.file.Path;

public class StringUtils {

	/**
	 * Calculates the similarity (a number within 0 and 1) between two strings.
	 */
	public static double similarity(String s1, String s2) {
		String longer = s1, shorter = s2;
		if (s1.length() < s2.length()) {
			longer = s2;
			shorter = s1;
		}
		int longerLength = longer.length();
		if (longerLength == 0) {
			/* both strings are zero length */
			return 1.0;
		}
		return (longerLength - editDistance(longer, shorter)) / (double) longerLength;
	}

	/**
	 * Example implementation of the Levenshtein Edit Distance See
	 * http://rosettacode.org/wiki/Levenshtein_distance#Java
	 * 
	 * @param s1
	 * @param s2
	 * @return
	 */
	public static int editDistance(String s1, String s2) {
		s1 = s1.toLowerCase();
		s2 = s2.toLowerCase();

		int[] costs = new int[s2.length() + 1];
		for (int i = 0; i <= s1.length(); i++) {
			int lastValue = i;
			for (int j = 0; j <= s2.length(); j++) {
				if (i == 0)
					costs[j] = j;
				else {
					if (j > 0) {
						int newValue = costs[j - 1];
						if (s1.charAt(i - 1) != s2.charAt(j - 1))
							newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
						costs[j - 1] = lastValue;
						lastValue = newValue;
					}
				}
			}
			if (i > 0)
				costs[s2.length()] = lastValue;
		}
		return costs[s2.length()];
	}

	public static String printSimilarity(String s, String t) {
		return String.format("%.3f is the similarity between \"%s\" and \"%s\"", similarity(s, t), s, t);
	}
	
	public static String extractFileNameWithoutExtension(File file) {
        Path path = file.toPath();
        String fileNameWithExtension = path.getFileName().toString();
        int dotIndex = fileNameWithExtension.lastIndexOf('.');
        if (dotIndex > 0) {
            return fileNameWithExtension.substring(0, dotIndex);
        } else {
            return fileNameWithExtension;
        }
    }

}
