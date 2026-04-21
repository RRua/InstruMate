import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Text,
  SimpleGrid,
  Badge,
  HStack,
  VStack,
  Icon,
  Spinner,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { useHistory } from "react-router-dom";
import { MdShield, MdAndroid, MdRefresh } from "react-icons/md";
import Card from "components/card/Card";
import {
  listApps,
  getHealth,
  submitToVirusTotal,
  getVTJob,
  getVTReport,
} from "api";

export default function VirusTotalHub() {
  const [apps, setApps] = useState([]);
  const [vtConfigured, setVtConfigured] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scanningApps, setScanningApps] = useState({});

  const textColor = useColorModeValue("secondaryGray.900", "white");
  const secondaryText = useColorModeValue("secondaryGray.600", "secondaryGray.500");
  const cardHover = useColorModeValue("gray.50", "navy.700");
  const history = useHistory();

  const loadApps = useCallback(async () => {
    try {
      const [appData, health] = await Promise.all([
        listApps({ per_page: 200 }),
        getHealth().catch(() => null),
      ]);
      if (health) setVtConfigured(!!health.virustotal_configured);

      // Use summary flags — no N+1 getAppDetail calls needed
      const items = appData.items || [];
      const enriched = await Promise.all(
        items.map(async (app) => {
          let vtReport = null;
          if (app.has_virustotal_report) {
            vtReport = await getVTReport(app.app_id).catch(() => null);
          }
          return { ...app, vtReport };
        })
      );
      setApps(enriched);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadApps(); }, [loadApps]);

  const handleScan = async (appId) => {
    setScanningApps((prev) => ({ ...prev, [appId]: { status: "running", message: "Submitting..." } }));
    try {
      const job = await submitToVirusTotal(appId);
      // eslint-disable-next-line no-constant-condition
      while (true) {
        await new Promise((r) => setTimeout(r, 3000));
        const result = await getVTJob(job.job_id);
        setScanningApps((prev) => ({
          ...prev,
          [appId]: { status: result.status === "completed" ? "done" : result.status === "failed" ? "error" : "running", message: result.message || result.status },
        }));
        if (result.status === "completed") {
          const vtReport = await getVTReport(appId).catch(() => null);
          setApps((prev) =>
            prev.map((a) =>
              a.app_id === appId
                ? { ...a, vtReport, has_virustotal_report: true }
                : a
            )
          );
          return;
        }
        if (result.status === "failed") return;
      }
    } catch (err) {
      setScanningApps((prev) => ({ ...prev, [appId]: { status: "error", message: err.message } }));
    }
  };

  const scannedApps = apps.filter((a) => a.vtReport);
  const flaggedApps = scannedApps.filter((a) => {
    const m = a.vtReport?.stats?.malicious || 0;
    const s = a.vtReport?.stats?.suspicious || 0;
    return m + s > 0;
  });
  const cleanApps = scannedApps.filter((a) => {
    const m = a.vtReport?.stats?.malicious || 0;
    const s = a.vtReport?.stats?.suspicious || 0;
    return m + s === 0;
  });

  if (loading) {
    return (
      <Box pt={{ base: "130px", md: "80px", xl: "80px" }} textAlign="center">
        <Spinner size="xl" color="cyan.500" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
        <Card p="30px"><Text color="red.500">{error}</Text></Card>
      </Box>
    );
  }

  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
      <HStack justify="space-between" mb="20px" flexWrap="wrap" gap="10px">
        <HStack>
          <Icon as={MdShield} w="28px" h="28px" color="cyan.500" />
          <Text fontSize="2xl" fontWeight="bold" color={textColor}>
            VirusTotal Scanner
          </Text>
        </HStack>
        <Button
          size="sm"
          leftIcon={<MdRefresh />}
          variant="outline"
          colorScheme="cyan"
          onClick={() => { setLoading(true); loadApps(); }}
        >
          Refresh
        </Button>
      </HStack>

      {!vtConfigured && (
        <Alert status="warning" borderRadius="12px" mb="20px">
          <AlertIcon />
          VT_API_KEY is not configured. Set it in your environment or docker-compose.yml to enable scanning.
        </Alert>
      )}

      <SimpleGrid columns={{ base: 2, md: 4 }} gap="16px" mb="20px">
        <Card p="16px" textAlign="center">
          <Text fontSize="xs" color={secondaryText} mb="4px">Total Apps</Text>
          <Text fontSize="2xl" fontWeight="bold" color={textColor}>{apps.length}</Text>
        </Card>
        <Card p="16px" textAlign="center">
          <Text fontSize="xs" color={secondaryText} mb="4px">VT Scanned</Text>
          <Text fontSize="2xl" fontWeight="bold" color="cyan.500">{scannedApps.length}</Text>
        </Card>
        <Card p="16px" textAlign="center">
          <Text fontSize="xs" color={secondaryText} mb="4px">Clean</Text>
          <Text fontSize="2xl" fontWeight="bold" color="green.500">{cleanApps.length}</Text>
        </Card>
        <Card p="16px" textAlign="center">
          <Text fontSize="xs" color={secondaryText} mb="4px">Flagged</Text>
          <Text fontSize="2xl" fontWeight="bold" color="red.500">{flaggedApps.length}</Text>
        </Card>
      </SimpleGrid>

      {apps.length === 0 ? (
        <Card p="40px" textAlign="center">
          <Icon as={MdAndroid} w="48px" h="48px" color="secondaryGray.400" mb="10px" />
          <Text color={secondaryText}>No apps analyzed yet. Upload an APK to get started.</Text>
        </Card>
      ) : (
        <Card p="0" overflow="hidden">
          <Box overflow="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>App</Th>
                  <Th>Version</Th>
                  <Th>VT Status</Th>
                  <Th>Detection</Th>
                  <Th>Malicious</Th>
                  <Th>Scan Date</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {apps.map((app) => {
                  const vt = app.vtReport;
                  const scanning = scanningApps[app.app_id];
                  const malicious = vt?.stats?.malicious || 0;
                  const suspicious = vt?.stats?.suspicious || 0;
                  const detected = malicious + suspicious;
                  const ratioColor =
                    !vt ? "gray" : detected === 0 ? "green" : detected <= 5 ? "yellow" : detected <= 15 ? "orange" : "red";

                  return (
                    <Tr
                      key={app.app_id}
                      _hover={{ bg: cardHover }}
                      cursor="pointer"
                      onClick={() => history.push(`/admin/apps/${app.app_id}`)}
                    >
                      <Td>
                        <VStack align="start" spacing="2px">
                          <Text fontSize="sm" fontWeight="600" color={textColor} noOfLines={1}>
                            {app.package_name}
                          </Text>
                          <Text fontSize="xs" color={secondaryText}>{app.app_id.slice(0, 12)}...</Text>
                        </VStack>
                      </Td>
                      <Td>
                        <HStack spacing="4px">
                          {app.version_name && <Badge colorScheme="blue" fontSize="xs">v{app.version_name}</Badge>}
                          {app.is_variant && <Badge colorScheme="orange" fontSize="xs">variant</Badge>}
                        </HStack>
                      </Td>
                      <Td>
                        {vt ? (
                          <Badge colorScheme="cyan" fontSize="xs">Scanned</Badge>
                        ) : scanning?.status === "running" ? (
                          <HStack spacing="6px">
                            <Spinner size="xs" color="cyan.500" />
                            <Text fontSize="xs" color={secondaryText}>{scanning.message}</Text>
                          </HStack>
                        ) : scanning?.status === "error" ? (
                          <Badge colorScheme="red" fontSize="xs">Error</Badge>
                        ) : (
                          <Badge colorScheme="gray" fontSize="xs">Not scanned</Badge>
                        )}
                      </Td>
                      <Td>
                        {vt ? (
                          <Badge colorScheme={ratioColor} fontSize="sm" px="8px">
                            {vt.detection_ratio}
                          </Badge>
                        ) : (
                          <Text fontSize="xs" color={secondaryText}>-</Text>
                        )}
                      </Td>
                      <Td>
                        {vt ? (
                          <Text fontSize="sm" color={detected > 0 ? "red.500" : "green.500"} fontWeight="600">
                            {detected}
                          </Text>
                        ) : (
                          <Text fontSize="xs" color={secondaryText}>-</Text>
                        )}
                      </Td>
                      <Td>
                        {vt?.scan_date ? (
                          <Text fontSize="xs" color={secondaryText}>
                            {new Date(vt.scan_date).toLocaleDateString()}
                          </Text>
                        ) : (
                          <Text fontSize="xs" color={secondaryText}>-</Text>
                        )}
                      </Td>
                      <Td onClick={(e) => e.stopPropagation()}>
                        {!vt && vtConfigured && (
                          <Button
                            size="xs"
                            colorScheme="cyan"
                            onClick={() => handleScan(app.app_id)}
                            isLoading={scanning?.status === "running"}
                            isDisabled={scanning?.status === "running"}
                          >
                            Scan
                          </Button>
                        )}
                        {vt?.permalink && (
                          <Button
                            as="a"
                            href={vt.permalink}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="outline"
                            colorScheme="cyan"
                            onClick={(e) => e.stopPropagation()}
                          >
                            VT Link
                          </Button>
                        )}
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </Box>
        </Card>
      )}
    </Box>
  );
}
