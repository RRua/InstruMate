import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Button,
  Text,
  useColorModeValue,
  VStack,
  HStack,
  Icon,
  Progress,
  CheckboxGroup,
  Checkbox,
  SimpleGrid,
} from "@chakra-ui/react";
import { useHistory } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { MdCloudUpload, MdCheckCircle, MdError, MdShield } from "react-icons/md";
import Card from "components/card/Card";
import { uploadAndAnalyze, getAnalysisJob, getHealth, submitToVirusTotal, getVTJob } from "api";

const ANALYZERS = [
  { value: "basic", label: "Basic", description: "Package info, permissions, activities" },
  { value: "callgraph", label: "Call Graph", description: "Method call graph extraction" },
  { value: "andex", label: "DEX Analysis", description: "DEX bytecode static analysis" },
  { value: "content++", label: "Content Types", description: "File type detection (full)" },
  { value: "possible_modifications", label: "Modifications", description: "Detect possible modifications" },
];

export default function Upload() {
  const [selectedAnalyzers, setSelectedAnalyzers] = useState([
    "basic", "callgraph", "andex", "content++", "possible_modifications",
  ]);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | analyzing | done | error
  const [message, setMessage] = useState("");
  const [appId, setAppId] = useState(null);
  const [autoVT, setAutoVT] = useState(false);
  const [vtConfigured, setVtConfigured] = useState(false);
  const [vtStatus, setVtStatus] = useState("idle"); // idle | running | done | error
  const [vtMessage, setVtMessage] = useState("");

  const history = useHistory();
  const borderColor = useColorModeValue("gray.200", "whiteAlpha.200");
  const dropBg = useColorModeValue("gray.50", "navy.800");
  const textColor = useColorModeValue("secondaryGray.900", "white");

  useEffect(() => {
    getHealth()
      .then((h) => setVtConfigured(!!h.virustotal_configured))
      .catch(() => {});
  }, []);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
      setStatus("idle");
      setMessage("");
      setAppId(null);
      setVtStatus("idle");
      setVtMessage("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ".apk",
    maxFiles: 1,
  });

  const pollJob = async (jobId) => {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const job = await getAnalysisJob(jobId);
        setMessage(job.message || job.status);
        if (job.status === "completed") {
          setStatus("done");
          setAppId(job.app_id);
          return job.app_id;
        }
        if (job.status === "failed") {
          setStatus("error");
          return null;
        }
      } catch (err) {
        setStatus("error");
        setMessage(err.message);
        return null;
      }
    }
  };

  const runVTScan = async (targetAppId) => {
    setVtStatus("running");
    setVtMessage("Submitting to VirusTotal...");
    try {
      const job = await submitToVirusTotal(targetAppId);
      // eslint-disable-next-line no-constant-condition
      while (true) {
        await new Promise((r) => setTimeout(r, 3000));
        const result = await getVTJob(job.job_id);
        setVtMessage(result.message || result.status);
        if (result.status === "completed") {
          setVtStatus("done");
          return;
        }
        if (result.status === "failed") {
          setVtStatus("error");
          return;
        }
      }
    } catch (err) {
      setVtStatus("error");
      setVtMessage(err.message);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setMessage("Uploading APK...");
    try {
      const result = await uploadAndAnalyze(file, selectedAnalyzers.join(","));
      setStatus("analyzing");
      setMessage("Analysis started...");
      const completedAppId = await pollJob(result.job_id);

      // Auto-submit to VT if enabled and analysis succeeded
      if (completedAppId && autoVT && vtConfigured) {
        await runVTScan(completedAppId);
      }
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  };

  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
      <SimpleGrid columns={1} gap="20px">
        <Card p="30px">
          <Text fontSize="2xl" fontWeight="bold" color={textColor} mb="20px">
            Upload APK for Analysis
          </Text>

          {/* Dropzone */}
          <Box
            {...getRootProps()}
            border="2px dashed"
            borderColor={isDragActive ? "brand.500" : borderColor}
            borderRadius="16px"
            bg={dropBg}
            p="40px"
            textAlign="center"
            cursor="pointer"
            transition="all 0.2s"
            _hover={{ borderColor: "brand.400" }}
            mb="20px"
          >
            <input {...getInputProps()} />
            <Icon as={MdCloudUpload} w="48px" h="48px" color="brand.500" mb="10px" />
            {file ? (
              <Text color={textColor} fontWeight="500">{file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)</Text>
            ) : isDragActive ? (
              <Text color={textColor}>Drop the APK here...</Text>
            ) : (
              <VStack spacing="4px">
                <Text color={textColor} fontWeight="500">Drag & drop an APK file here</Text>
                <Text color="secondaryGray.600" fontSize="sm">or click to browse</Text>
              </VStack>
            )}
          </Box>

          {/* Analyzer selection */}
          <Text fontSize="md" fontWeight="600" color={textColor} mb="10px">
            Analyzers
          </Text>
          <CheckboxGroup value={selectedAnalyzers} onChange={setSelectedAnalyzers}>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing="10px" mb="20px">
              {ANALYZERS.map((a) => (
                <Checkbox key={a.value} value={a.value} colorScheme="brandScheme">
                  <Box>
                    <Text fontSize="sm" fontWeight="500">{a.label}</Text>
                    <Text fontSize="xs" color="secondaryGray.600">{a.description}</Text>
                  </Box>
                </Checkbox>
              ))}
            </SimpleGrid>
          </CheckboxGroup>

          {/* VirusTotal auto-scan option */}
          <Box
            mb="20px"
            p="12px"
            borderRadius="12px"
            border="1px solid"
            borderColor={vtConfigured ? "cyan.200" : "gray.200"}
            opacity={vtConfigured ? 1 : 0.6}
          >
            <Checkbox
              isChecked={autoVT}
              onChange={(e) => setAutoVT(e.target.checked)}
              colorScheme="cyan"
              isDisabled={!vtConfigured}
            >
              <HStack spacing="8px">
                <Icon as={MdShield} color="cyan.500" w="18px" h="18px" />
                <Box>
                  <Text fontSize="sm" fontWeight="500" color={textColor}>
                    Auto-submit to VirusTotal
                  </Text>
                  <Text fontSize="xs" color="secondaryGray.600">
                    {vtConfigured
                      ? "Automatically scan the APK with 70+ antivirus engines after analysis"
                      : "VT_API_KEY not configured — set it to enable VirusTotal scanning"}
                  </Text>
                </Box>
              </HStack>
            </Checkbox>
          </Box>

          {/* Upload button */}
          <Button
            colorScheme="brandScheme"
            size="lg"
            onClick={handleUpload}
            isDisabled={!file || status === "uploading" || status === "analyzing"}
            isLoading={status === "uploading" || status === "analyzing"}
            loadingText={status === "uploading" ? "Uploading..." : "Analyzing..."}
            w={{ base: "100%", md: "auto" }}
          >
            Upload & Analyze
          </Button>

          {/* Status */}
          {status !== "idle" && (
            <Box mt="20px">
              {(status === "uploading" || status === "analyzing") && (
                <Progress size="sm" isIndeterminate colorScheme="brandScheme" borderRadius="full" mb="10px" />
              )}
              <HStack>
                {status === "done" && <Icon as={MdCheckCircle} color="green.500" w="20px" h="20px" />}
                {status === "error" && <Icon as={MdError} color="red.500" w="20px" h="20px" />}
                <Text fontSize="sm" color={status === "error" ? "red.500" : textColor}>
                  {message}
                </Text>
              </HStack>

              {/* VT scan status */}
              {vtStatus === "running" && (
                <HStack mt="10px">
                  <Icon as={MdShield} color="cyan.500" w="16px" h="16px" />
                  <Progress size="sm" isIndeterminate colorScheme="cyan" borderRadius="full" flex={1} />
                  <Text fontSize="sm" color={textColor}>{vtMessage}</Text>
                </HStack>
              )}
              {vtStatus === "done" && (
                <HStack mt="10px">
                  <Icon as={MdShield} color="cyan.500" w="16px" h="16px" />
                  <Icon as={MdCheckCircle} color="green.500" w="16px" h="16px" />
                  <Text fontSize="sm" color="green.500">VirusTotal scan complete</Text>
                </HStack>
              )}
              {vtStatus === "error" && (
                <HStack mt="10px">
                  <Icon as={MdShield} color="cyan.500" w="16px" h="16px" />
                  <Icon as={MdError} color="red.500" w="16px" h="16px" />
                  <Text fontSize="sm" color="red.500">{vtMessage}</Text>
                </HStack>
              )}

              {status === "done" && appId && (
                <Button
                  mt="10px"
                  variant="outline"
                  colorScheme="brandScheme"
                  size="sm"
                  onClick={() => history.push(`/admin/apps/${appId}`)}
                >
                  View Results
                </Button>
              )}
            </Box>
          )}
        </Card>
      </SimpleGrid>
    </Box>
  );
}
