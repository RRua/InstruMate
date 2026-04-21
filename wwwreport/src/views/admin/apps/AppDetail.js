import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Text,
  SimpleGrid,
  Badge,
  HStack,
  VStack,
  Spinner,
  Button,
  useColorModeValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Code,
  Wrap,
  WrapItem,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import {
  MdSecurity,
  MdBugReport,
  MdCode,
  MdAccountTree,
  MdFolder,
  MdShield,
  MdWarning,
} from "react-icons/md";
import Card from "components/card/Card";
import { useHistory } from "react-router-dom";
import {
  getAppDetail,
  getAppAnalysis,
  triggerClassification,
  getClassifyJob,
  getClassification,
  getSecurityMetrics,
  getHealth,
  submitToVirusTotal,
  getVTJob,
  getVTReport,
  getDownloadUrl,
  getExportUrl,
} from "api";
import {
  MdDownload,
  MdFileDownload,
  MdAccountTree as MdCallGraph,
} from "react-icons/md";

/* ──────────── Helpers ──────────── */

const RISK_COLORS = { low: "green", medium: "yellow", high: "orange", critical: "red" };
const MALWARE_COLORS = { benign: "green", suspicious: "orange", likely_malicious: "red" };

function RiskBadge({ level }) {
  return <Badge colorScheme={RISK_COLORS[level] || "gray"} fontSize="sm" px="8px" py="2px">{level}</Badge>;
}

function StatCard({ label, value, helpText, icon, color }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");
  return (
    <Card p="16px">
      <HStack spacing="12px">
        {icon && <Icon as={icon} w="28px" h="28px" color={color || "brand.500"} />}
        <Stat>
          <StatLabel fontSize="xs" color="secondaryGray.600">{label}</StatLabel>
          <StatNumber fontSize="xl" color={textColor}>{value}</StatNumber>
          {helpText && <StatHelpText mb="0">{helpText}</StatHelpText>}
        </Stat>
      </HStack>
    </Card>
  );
}

/* ──────────── Main Component ──────────── */

export default function AppDetail({ match }) {
  const appId = match.params.appId;
  const history = useHistory();
  const [detail, setDetail] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [classification, setClassification] = useState(null);
  const [classifyStatus, setClassifyStatus] = useState("idle");
  const [classifyMsg, setClassifyMsg] = useState("");
  const [vtReport, setVtReport] = useState(null);
  const [vtStatus, setVtStatus] = useState("idle");
  const [vtMsg, setVtMsg] = useState("");
  const [vtConfigured, setVtConfigured] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const textColor = useColorModeValue("secondaryGray.900", "white");
  const secondaryText = useColorModeValue("secondaryGray.600", "secondaryGray.500");
  // Load all data
  useEffect(() => {
    Promise.all([
      getAppDetail(appId),
      getAppAnalysis(appId).catch(() => null),
      getHealth().catch(() => null),
    ]).then(([d, a, h]) => {
      setDetail(d);
      setAnalysis(a);
      if (h) setVtConfigured(!!h.virustotal_configured);
      // Try to load existing classification / metrics
      if (d.has_security_metrics) getSecurityMetrics(appId).then(setMetrics).catch(() => {});
      if (d.has_classification) getClassification(appId).then(setClassification).catch(() => {});
      if (d.has_virustotal_report) getVTReport(appId).then(setVtReport).catch(() => {});
      setLoading(false);
    }).catch((err) => { setError(err.message); setLoading(false); });
  }, [appId]);

  // Classification polling
  const pollClassifyJob = useCallback(async (jobId) => {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const job = await getClassifyJob(jobId);
        setClassifyMsg(job.message || job.status);
        if (job.status === "completed") {
          setClassifyStatus("done");
          getSecurityMetrics(appId).then(setMetrics).catch(() => {});
          getClassification(appId).then(setClassification).catch(() => {});
          return;
        }
        if (job.status === "failed") {
          setClassifyStatus("error");
          return;
        }
      } catch (err) {
        setClassifyStatus("error");
        setClassifyMsg(err.message);
        return;
      }
    }
  }, [appId]);

  const handleClassify = async () => {
    setClassifyStatus("running");
    setClassifyMsg("Starting classification...");
    try {
      const job = await triggerClassification(appId);
      await pollClassifyJob(job.job_id);
    } catch (err) {
      setClassifyStatus("error");
      setClassifyMsg(err.message);
    }
  };

  // VirusTotal polling
  const pollVTJob = useCallback(async (jobId) => {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      await new Promise((r) => setTimeout(r, 3000));
      try {
        const job = await getVTJob(jobId);
        setVtMsg(job.message || job.status);
        if (job.status === "completed") {
          setVtStatus("done");
          getVTReport(appId).then(setVtReport).catch(() => {});
          return;
        }
        if (job.status === "failed") {
          setVtStatus("error");
          return;
        }
      } catch (err) {
        setVtStatus("error");
        setVtMsg(err.message);
        return;
      }
    }
  }, [appId]);

  const handleVTScan = async () => {
    setVtStatus("running");
    setVtMsg("Submitting to VirusTotal...");
    try {
      const job = await submitToVirusTotal(appId);
      await pollVTJob(job.job_id);
    } catch (err) {
      setVtStatus("error");
      setVtMsg(err.message);
    }
  };

  if (loading) {
    return (
      <Box pt={{ base: "130px", md: "80px", xl: "80px" }} textAlign="center">
        <Spinner size="xl" color="brand.500" />
      </Box>
    );
  }

  if (error || !detail) {
    return (
      <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
        <Card p="30px"><Text color="red.500">{error || "App not found"}</Text></Card>
      </Box>
    );
  }

  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
      {/* ── Header ── */}
      <Card p="24px" mb="20px">
        <HStack justify="space-between" align="start" flexWrap="wrap" gap="12px">
          <VStack align="start" spacing="6px">
            <Text fontSize="2xl" fontWeight="bold" color={textColor}>
              {detail.app_name || detail.package_name}
            </Text>
            <Text fontSize="sm" color={secondaryText}>{detail.package_name}</Text>
            <HStack spacing="8px" flexWrap="wrap">
              {detail.version_name && <Badge colorScheme="blue">v{detail.version_name}</Badge>}
              {detail.version_code && <Badge colorScheme="gray">code {detail.version_code}</Badge>}
              {detail.is_variant && <Badge colorScheme="orange">variant</Badge>}
              {detail.target_sdk_version && <Badge colorScheme="purple">SDK {detail.target_sdk_version}</Badge>}
              {detail.min_sdk_version && <Badge colorScheme="gray">min SDK {detail.min_sdk_version}</Badge>}
            </HStack>
          </VStack>
          <VStack align="end" spacing="6px">
            <Text fontSize="xs" color={secondaryText}>ID: {detail.app_id}</Text>
            <HStack>
              {detail.has_content_type_analysis && <Badge colorScheme="green" variant="subtle">Content</Badge>}
              {detail.has_dex_analysis && <Badge colorScheme="green" variant="subtle">DEX</Badge>}
              {detail.has_call_graph && <Badge colorScheme="green" variant="subtle">Call Graph</Badge>}
              {detail.has_security_metrics && <Badge colorScheme="teal" variant="subtle">Metrics</Badge>}
              {detail.has_classification && <Badge colorScheme="teal" variant="subtle">Classified</Badge>}
              {detail.has_virustotal_report && <Badge colorScheme="cyan" variant="subtle">VirusTotal</Badge>}
            </HStack>
            <HStack spacing="8px">
              {detail.has_call_graph && (
                <Button
                  size="xs"
                  leftIcon={<MdCallGraph />}
                  colorScheme="purple"
                  variant="outline"
                  onClick={() => history.push(`/admin/graph/${appId}`)}
                >
                  View Call Graph
                </Button>
              )}
              <Button
                as="a"
                href={getDownloadUrl(appId)}
                size="xs"
                leftIcon={<MdDownload />}
                colorScheme="blue"
                variant="outline"
              >
                Download APK
              </Button>
              <Button
                as="a"
                href={getExportUrl(appId)}
                size="xs"
                leftIcon={<MdFileDownload />}
                colorScheme="green"
                variant="outline"
              >
                Export Results
              </Button>
            </HStack>
          </VStack>
        </HStack>
      </Card>

      {/* ── Classification Banner ── */}
      {classification ? (
        <Card p="24px" mb="20px" borderLeft="4px solid" borderLeftColor={`${RISK_COLORS[classification.security_risk_level]}.500`}>
          <SimpleGrid columns={{ base: 1, md: 4 }} gap="20px">
            <StatCard
              label="Security Risk"
              value={classification.security_risk_level?.toUpperCase()}
              icon={MdSecurity}
              color={`${RISK_COLORS[classification.security_risk_level]}.500`}
            />
            <StatCard
              label="Malware Likelihood"
              value={classification.malware_likelihood?.replace("_", " ")}
              icon={MdBugReport}
              color={`${MALWARE_COLORS[classification.malware_likelihood]}.500`}
            />
            <StatCard
              label="Confidence"
              value={`${((classification.confidence || 0) * 100).toFixed(0)}%`}
              icon={MdShield}
            />
            <StatCard
              label="Model"
              value={classification.model_used || "N/A"}
              icon={MdCode}
            />
          </SimpleGrid>
          {classification.reasoning && (
            <Box mt="16px">
              <Text fontSize="sm" fontWeight="600" color={textColor} mb="4px">Reasoning</Text>
              <Text fontSize="sm" color={secondaryText}>{classification.reasoning}</Text>
            </Box>
          )}
          {classification.risk_factors?.length > 0 && (
            <Box mt="12px">
              <Text fontSize="sm" fontWeight="600" color={textColor} mb="6px">Risk Factors</Text>
              <VStack align="start" spacing="4px">
                {classification.risk_factors.map((rf, i) => (
                  <HStack key={i}>
                    <RiskBadge level={rf.severity} />
                    <Text fontSize="sm" color={secondaryText}>
                      <strong>{rf.category}:</strong> {rf.description}
                    </Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}
          {classification.recommendations?.length > 0 && (
            <Box mt="12px">
              <Text fontSize="sm" fontWeight="600" color={textColor} mb="6px">Recommendations</Text>
              <VStack align="start" spacing="2px">
                {classification.recommendations.map((r, i) => (
                  <Text key={i} fontSize="sm" color={secondaryText}>• {r}</Text>
                ))}
              </VStack>
            </Box>
          )}
        </Card>
      ) : (
        <Card p="20px" mb="20px">
          <HStack justify="space-between" flexWrap="wrap" gap="10px">
            <HStack>
              <Icon as={MdSecurity} w="24px" h="24px" color="brand.500" />
              <Text fontWeight="600" color={textColor}>Security Classification</Text>
            </HStack>
            <HStack>
              {classifyStatus === "running" && (
                <>
                  <Spinner size="sm" color="brand.500" />
                  <Text fontSize="sm" color={secondaryText}>{classifyMsg}</Text>
                </>
              )}
              {classifyStatus === "error" && (
                <Text fontSize="sm" color="red.500">{classifyMsg}</Text>
              )}
              {classifyStatus === "done" && (
                <Text fontSize="sm" color="green.500">Classification complete</Text>
              )}
              <Button
                size="sm"
                colorScheme="brandScheme"
                onClick={handleClassify}
                isLoading={classifyStatus === "running"}
                isDisabled={classifyStatus === "running"}
              >
                Run Classification
              </Button>
            </HStack>
          </HStack>
        </Card>
      )}

      {/* ── VirusTotal Section ── */}
      {vtReport ? (
        <VirusTotalResultCard report={vtReport} textColor={textColor} secondaryText={secondaryText} />
      ) : (
        <Card p="20px" mb="20px">
          <HStack justify="space-between" flexWrap="wrap" gap="10px">
            <HStack>
              <Icon as={MdShield} w="24px" h="24px" color="cyan.500" />
              <Text fontWeight="600" color={textColor}>VirusTotal Scan</Text>
            </HStack>
            <HStack>
              {vtStatus === "running" && (
                <>
                  <Spinner size="sm" color="cyan.500" />
                  <Text fontSize="sm" color={secondaryText}>{vtMsg}</Text>
                </>
              )}
              {vtStatus === "error" && (
                <Text fontSize="sm" color="red.500">{vtMsg}</Text>
              )}
              {vtStatus === "done" && (
                <Text fontSize="sm" color="green.500">Scan complete</Text>
              )}
              {vtConfigured ? (
                <Button
                  size="sm"
                  colorScheme="cyan"
                  onClick={handleVTScan}
                  isLoading={vtStatus === "running"}
                  isDisabled={vtStatus === "running"}
                >
                  Submit to VirusTotal
                </Button>
              ) : (
                <Button size="sm" colorScheme="gray" isDisabled>
                  VT API Key Required
                </Button>
              )}
            </HStack>
          </HStack>
        </Card>
      )}

      {/* ── Tabs for detailed reports ── */}
      <Card p="0" overflow="hidden">
        <Tabs colorScheme="brandScheme" isLazy>
          <TabList px="20px" pt="10px" overflowX="auto">
            <Tab>Overview</Tab>
            {metrics && <Tab>Security Metrics</Tab>}
            {analysis?.content_type_analysis && <Tab>Content Types</Tab>}
            {analysis?.dex_static_analysis && <Tab>DEX Analysis</Tab>}
            {analysis?.possible_modifications && <Tab>Modifications</Tab>}
          </TabList>
          <TabPanels>
            {/* Overview */}
            <TabPanel>
              <OverviewTab detail={detail} metrics={metrics} />
            </TabPanel>

            {/* Security Metrics */}
            {metrics && (
              <TabPanel>
                <MetricsTab metrics={metrics} />
              </TabPanel>
            )}

            {/* Content Types */}
            {analysis?.content_type_analysis && (
              <TabPanel>
                <ContentTab data={analysis.content_type_analysis} />
              </TabPanel>
            )}

            {/* DEX Analysis */}
            {analysis?.dex_static_analysis && (
              <TabPanel>
                <DexTab data={analysis.dex_static_analysis} />
              </TabPanel>
            )}

            {/* Modifications */}
            {analysis?.possible_modifications && (
              <TabPanel>
                <ModificationsTab data={analysis.possible_modifications} />
              </TabPanel>
            )}
          </TabPanels>
        </Tabs>
      </Card>
    </Box>
  );
}

/* ──────────── VirusTotal Result Card ──────────── */

function VirusTotalResultCard({ report, textColor, secondaryText }) {
  const malicious = report.stats?.malicious || 0;
  const suspicious = report.stats?.suspicious || 0;
  const detected = malicious + suspicious;
  const ratioColor =
    detected === 0 ? "green" : detected <= 5 ? "yellow" : detected <= 15 ? "orange" : "red";

  // Collect engines with positive detections
  const positives = Object.entries(report.results || {})
    .filter(([, v]) => v.category === "malicious" || v.category === "suspicious")
    .sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <Card p="24px" mb="20px" borderLeft="4px solid" borderLeftColor={`${ratioColor}.500`}>
      <HStack justify="space-between" mb="16px" flexWrap="wrap" gap="8px">
        <HStack>
          <Icon as={MdShield} w="24px" h="24px" color="cyan.500" />
          <Text fontSize="lg" fontWeight="600" color={textColor}>VirusTotal Results</Text>
        </HStack>
        {report.permalink && (
          <Button
            as="a"
            href={report.permalink}
            target="_blank"
            rel="noopener noreferrer"
            size="xs"
            variant="outline"
            colorScheme="cyan"
          >
            View on VirusTotal
          </Button>
        )}
      </HStack>

      <SimpleGrid columns={{ base: 1, md: 4 }} gap="16px" mb="16px">
        <StatCard
          label="Detection Ratio"
          value={report.detection_ratio || `${detected}/?`}
          icon={MdShield}
          color={`${ratioColor}.500`}
        />
        <StatCard label="Malicious" value={malicious} icon={MdBugReport} color="red.500" />
        <StatCard label="Suspicious" value={suspicious} icon={MdWarning} color="orange.500" />
        <StatCard label="Undetected" value={report.stats?.undetected || 0} icon={MdSecurity} color="green.500" />
      </SimpleGrid>

      {report.scan_date && (
        <Text fontSize="xs" color={secondaryText} mb="12px">
          Scanned: {new Date(report.scan_date).toLocaleString()} | SHA-256: {report.sha256}
        </Text>
      )}

      {positives.length > 0 && (
        <Box>
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
            Positive Detections ({positives.length})
          </Text>
          <Box maxH="250px" overflow="auto">
            <Table variant="simple" size="sm">
              <Thead position="sticky" top={0} bg="white" zIndex={1}>
                <Tr>
                  <Th>Engine</Th>
                  <Th>Category</Th>
                  <Th>Detection</Th>
                </Tr>
              </Thead>
              <Tbody>
                {positives.map(([engine, info]) => (
                  <Tr key={engine}>
                    <Td fontSize="sm" fontWeight="500">{engine}</Td>
                    <Td>
                      <Badge colorScheme={info.category === "malicious" ? "red" : "orange"} fontSize="xs">
                        {info.category}
                      </Badge>
                    </Td>
                    <Td fontSize="xs"><Code>{info.result || "N/A"}</Code></Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </Box>
      )}

      {positives.length === 0 && detected === 0 && (
        <Alert status="success" borderRadius="8px">
          <AlertIcon />
          No engines detected this file as malicious.
        </Alert>
      )}
    </Card>
  );
}

/* ──────────── Tab Components ──────────── */

function OverviewTab({ detail, metrics }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");
  return (
    <SimpleGrid columns={{ base: 1, md: 2 }} gap="20px">
      {/* App Info */}
      <Box>
        <Text fontSize="lg" fontWeight="600" color={textColor} mb="12px">App Information</Text>
        <Table variant="simple" size="sm">
          <Tbody>
            <Tr><Td fontWeight="500">Package</Td><Td>{detail.package_name}</Td></Tr>
            <Tr><Td fontWeight="500">App Name</Td><Td>{detail.app_name || "N/A"}</Td></Tr>
            <Tr><Td fontWeight="500">Version</Td><Td>{detail.version_name} ({detail.version_code})</Td></Tr>
            <Tr><Td fontWeight="500">Main Activity</Td><Td><Code fontSize="xs">{detail.main_activity}</Code></Td></Tr>
            <Tr><Td fontWeight="500">Min SDK</Td><Td>{detail.min_sdk_version || "N/A"}</Td></Tr>
            <Tr><Td fontWeight="500">Target SDK</Td><Td>{detail.target_sdk_version || "N/A"}</Td></Tr>
            <Tr><Td fontWeight="500">Max SDK</Td><Td>{detail.max_sdk_version || "N/A"}</Td></Tr>
          </Tbody>
        </Table>
      </Box>

      {/* Permissions */}
      <Box>
        <Text fontSize="lg" fontWeight="600" color={textColor} mb="12px">
          Permissions ({detail.permissions?.length || 0})
        </Text>
        {detail.permissions?.length > 0 ? (
          <Wrap spacing="6px">
            {detail.permissions.map((p, i) => {
              const short = p.replace("android.permission.", "");
              return <WrapItem key={i}><Badge colorScheme="gray" fontSize="xs">{short}</Badge></WrapItem>;
            })}
          </Wrap>
        ) : (
          <Text fontSize="sm" color="secondaryGray.500">No permissions declared</Text>
        )}

        {/* Activities */}
        <Text fontSize="lg" fontWeight="600" color={textColor} mt="20px" mb="12px">
          Activities ({detail.activities?.length || 0})
        </Text>
        <Box maxH="200px" overflow="auto">
          {detail.activities?.map((a, i) => (
            <Text key={i} fontSize="xs" fontFamily="mono" mb="2px">{a}</Text>
          ))}
        </Box>

        {/* Services */}
        {detail.services?.length > 0 && (
          <>
            <Text fontSize="lg" fontWeight="600" color={textColor} mt="20px" mb="12px">
              Services ({detail.services.length})
            </Text>
            <Box maxH="150px" overflow="auto">
              {detail.services.map((s, i) => (
                <Text key={i} fontSize="xs" fontFamily="mono" mb="2px">{s}</Text>
              ))}
            </Box>
          </>
        )}
      </Box>
    </SimpleGrid>
  );
}

function MetricsTab({ metrics }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");
  const perm = metrics.permissions || {};
  const code = metrics.code || {};
  const cg = metrics.call_graph || {};
  const content = metrics.content || {};

  return (
    <VStack align="stretch" spacing="20px">
      {/* Quick stats */}
      <SimpleGrid columns={{ base: 2, md: 4 }} gap="12px">
        <StatCard label="Permission Risk" value={((perm.permission_risk_score || 0) * 100).toFixed(0) + "%"} icon={MdSecurity} color="orange.500" />
        <StatCard label="Dangerous Perms" value={perm.dangerous_count || 0} icon={MdWarning} color="red.500" />
        <StatCard label="Suspicious APIs" value={code.suspicious_api_count || 0} icon={MdBugReport} color="orange.500" />
        <StatCard label="Obfuscation" value={((code.obfuscation_score || 0) * 100).toFixed(0) + "%"} icon={MdCode} color="purple.500" />
      </SimpleGrid>
      <SimpleGrid columns={{ base: 2, md: 4 }} gap="12px">
        <StatCard label="CG Nodes" value={cg.total_nodes || 0} icon={MdAccountTree} />
        <StatCard label="CG Edges" value={cg.total_edges || 0} icon={MdAccountTree} />
        <StatCard label="Sensitive APIs" value={cg.sensitive_api_count || 0} icon={MdWarning} color="red.500" />
        <StatCard label="Total Files" value={content.total_files || 0} icon={MdFolder} />
      </SimpleGrid>

      {/* Permission details */}
      {perm.dangerous_permissions?.length > 0 && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Dangerous Permissions</Text>
          <Wrap spacing="6px">
            {perm.dangerous_permissions.map((p, i) => (
              <WrapItem key={i}><Badge colorScheme="red" fontSize="xs">{p.replace("android.permission.", "")}</Badge></WrapItem>
            ))}
          </Wrap>
        </Box>
      )}

      {/* Suspicious combos */}
      {perm.suspicious_combinations?.length > 0 && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Suspicious Permission Combinations</Text>
          {perm.suspicious_combinations.map((c, i) => (
            <Alert key={i} status="warning" borderRadius="8px" mb="8px" fontSize="sm">
              <AlertIcon /><strong>{c.name}:</strong>&nbsp;{c.description}
            </Alert>
          ))}
        </Box>
      )}

      {/* Suspicious APIs */}
      {code.suspicious_api_calls && Object.keys(code.suspicious_api_calls).length > 0 && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Suspicious API Calls</Text>
          <Accordion allowMultiple>
            {Object.entries(code.suspicious_api_calls).map(([cat, calls]) => (
              <AccordionItem key={cat}>
                <AccordionButton>
                  <Box flex="1" textAlign="left" fontSize="sm" fontWeight="500">
                    {cat} ({calls.length})
                  </Box>
                  <AccordionIcon />
                </AccordionButton>
                <AccordionPanel>
                  <Box maxH="200px" overflow="auto">
                    {calls.map((c, i) => (
                      <Code key={i} display="block" fontSize="xs" mb="2px" whiteSpace="pre-wrap">{c}</Code>
                    ))}
                  </Box>
                </AccordionPanel>
              </AccordionItem>
            ))}
          </Accordion>
        </Box>
      )}

      {/* Call graph sensitive families */}
      {cg.sensitive_api_reachability && Object.keys(cg.sensitive_api_reachability).length > 0 && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Sensitive API Reachability (Call Graph)</Text>
          <SimpleGrid columns={{ base: 2, md: 4 }} gap="8px">
            {Object.entries(cg.sensitive_api_reachability).map(([family, nodes]) => (
              <Badge key={family} colorScheme="orange" p="8px" borderRadius="8px" textAlign="center">
                {family}: {nodes.length}
              </Badge>
            ))}
          </SimpleGrid>
        </Box>
      )}

      {/* Content anomalies */}
      {(content.has_automation_scripts || content.has_crypto_materials || content.has_hidden_executables) && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Content Anomalies</Text>
          <HStack spacing="8px">
            {content.has_automation_scripts && <Badge colorScheme="orange">Automation Scripts</Badge>}
            {content.has_crypto_materials && <Badge colorScheme="red">Crypto Materials</Badge>}
            {content.has_hidden_executables && <Badge colorScheme="red">Hidden Executables</Badge>}
          </HStack>
        </Box>
      )}

      {/* Embedded URLs/IPs */}
      {(code.embedded_urls?.length > 0 || code.embedded_ips?.length > 0) && (
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="8px">Embedded Network Indicators</Text>
          {code.embedded_urls?.length > 0 && (
            <Accordion allowMultiple>
              <AccordionItem>
                <AccordionButton>
                  <Box flex="1" textAlign="left" fontSize="sm" fontWeight="500">URLs ({code.embedded_urls.length})</Box>
                  <AccordionIcon />
                </AccordionButton>
                <AccordionPanel>
                  <Box maxH="200px" overflow="auto">
                    {code.embedded_urls.map((u, i) => (
                      <Code key={i} display="block" fontSize="xs" mb="2px" wordBreak="break-all">{u}</Code>
                    ))}
                  </Box>
                </AccordionPanel>
              </AccordionItem>
            </Accordion>
          )}
          {code.embedded_ips?.length > 0 && (
            <Wrap mt="8px" spacing="6px">
              {code.embedded_ips.map((ip, i) => (
                <WrapItem key={i}><Badge colorScheme="gray">{ip}</Badge></WrapItem>
              ))}
            </Wrap>
          )}
        </Box>
      )}
    </VStack>
  );
}

function ContentTab({ data }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");
  if (!data || data.length === 0) return <Text color="secondaryGray.500">No content data</Text>;

  const columns = Object.keys(data[0]).filter(
    (k) => k !== "file_path" && k !== "file_name"
  );

  return (
    <Box>
      <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
        File Content Types ({data.length} files)
      </Text>
      <Box overflow="auto" maxH="500px">
        <Table variant="simple" size="sm">
          <Thead position="sticky" top={0} bg="white" zIndex={1}>
            <Tr>
              <Th>File</Th>
              {columns.slice(0, 8).map((c) => <Th key={c} fontSize="xs">{c.replace("is_", "")}</Th>)}
            </Tr>
          </Thead>
          <Tbody>
            {data.slice(0, 200).map((row, i) => (
              <Tr key={i}>
                <Td fontSize="xs" maxW="300px" isTruncated>{row.file_path || row.file_name || `file_${i}`}</Td>
                {columns.slice(0, 8).map((c) => (
                  <Td key={c} fontSize="xs">
                    {row[c] === "True" || row[c] === "true" || row[c] === true
                      ? <Badge colorScheme="green" size="sm">Y</Badge>
                      : ""}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
        {data.length > 200 && (
          <Text fontSize="xs" color="secondaryGray.500" mt="8px" textAlign="center">
            Showing first 200 of {data.length} files
          </Text>
        )}
      </Box>
    </Box>
  );
}

function DexTab({ data }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");

  // data can be a dict keyed by dex file or a list
  let dexEntries = [];
  if (Array.isArray(data)) {
    dexEntries = data.map((d, i) => [`dex_${i}`, d]);
  } else if (typeof data === "object") {
    dexEntries = Object.entries(data);
  }

  return (
    <Box>
      <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
        DEX Static Analysis ({dexEntries.length} files)
      </Text>
      <Accordion allowMultiple>
        {dexEntries.map(([name, dex]) => {
          const classes = dex?.classes || [];
          const methods = dex?.methods || [];
          const strings = dex?.strings || [];
          return (
            <AccordionItem key={name}>
              <AccordionButton>
                <Box flex="1" textAlign="left" fontWeight="500" fontSize="sm">
                  {name} — {classes.length} classes, {methods.length} methods, {strings.length} strings
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel>
                <SimpleGrid columns={{ base: 1, md: 2 }} gap="12px">
                  <Box>
                    <Text fontSize="sm" fontWeight="500" mb="4px">Classes ({classes.length})</Text>
                    <Box maxH="200px" overflow="auto" bg="gray.50" p="8px" borderRadius="8px">
                      {classes.slice(0, 100).map((c, i) => (
                        <Code key={i} display="block" fontSize="xs" mb="1px">{c}</Code>
                      ))}
                      {classes.length > 100 && <Text fontSize="xs" color="gray.500">...and {classes.length - 100} more</Text>}
                    </Box>
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="500" mb="4px">Strings ({strings.length})</Text>
                    <Box maxH="200px" overflow="auto" bg="gray.50" p="8px" borderRadius="8px">
                      {strings.slice(0, 100).map((s, i) => (
                        <Code key={i} display="block" fontSize="xs" mb="1px" whiteSpace="pre-wrap" wordBreak="break-all">{s}</Code>
                      ))}
                      {strings.length > 100 && <Text fontSize="xs" color="gray.500">...and {strings.length - 100} more</Text>}
                    </Box>
                  </Box>
                </SimpleGrid>
              </AccordionPanel>
            </AccordionItem>
          );
        })}
      </Accordion>
    </Box>
  );
}

function ModificationsTab({ data }) {
  const textColor = useColorModeValue("secondaryGray.900", "white");
  return (
    <Box>
      <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">Possible Modifications</Text>
      {Object.entries(data).map(([key, value]) => (
        <Box key={key} mb="16px">
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="4px">{key}</Text>
          {typeof value === "object" && value !== null ? (
            <Box bg="gray.50" p="12px" borderRadius="8px" maxH="300px" overflow="auto">
              <Code display="block" fontSize="xs" whiteSpace="pre-wrap">
                {JSON.stringify(value, null, 2)}
              </Code>
            </Box>
          ) : (
            <Text fontSize="sm">{String(value)}</Text>
          )}
        </Box>
      ))}
    </Box>
  );
}
