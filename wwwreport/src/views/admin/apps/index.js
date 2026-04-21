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
  Input,
  InputGroup,
  InputLeftElement,
  Button,
  ButtonGroup,
  useColorModeValue,
} from "@chakra-ui/react";
import { useHistory } from "react-router-dom";
import { MdAndroid, MdArrowForward, MdShield, MdSearch } from "react-icons/md";
import Card from "components/card/Card";
import { listApps } from "api";

export default function AppsList() {
  const [data, setData] = useState(null); // paginated response
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({});
  const perPage = 30;

  const textColor = useColorModeValue("secondaryGray.900", "white");
  const secondaryText = useColorModeValue("secondaryGray.600", "secondaryGray.500");
  const cardHover = useColorModeValue("gray.50", "navy.700");
  const history = useHistory();

  const fetchApps = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listApps({
        q: search || undefined,
        page,
        per_page: perPage,
        ...filters,
      });
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }, [search, page, filters]);

  useEffect(() => { fetchApps(); }, [fetchApps]);

  // Debounced search
  const [searchInput, setSearchInput] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const toggleFilter = (key, value) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (next[key] === value) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
    setPage(1);
  };

  const apps = data?.items || [];
  const total = data?.total || 0;
  const totalPages = data?.pages || 1;

  if (error && !data) {
    return (
      <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
        <Card p="30px"><Text color="red.500">{error}</Text></Card>
      </Box>
    );
  }

  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
      <HStack justify="space-between" mb="16px" flexWrap="wrap" gap="10px">
        <Text fontSize="2xl" fontWeight="bold" color={textColor}>
          Analyzed Apps {data ? `(${total})` : ""}
        </Text>
        <InputGroup maxW="300px">
          <InputLeftElement pointerEvents="none">
            <Icon as={MdSearch} color="secondaryGray.400" />
          </InputLeftElement>
          <Input
            placeholder="Search apps..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            size="md"
            borderRadius="12px"
          />
        </InputGroup>
      </HStack>

      {/* Filter badges */}
      <HStack spacing="8px" mb="16px" flexWrap="wrap">
        <Badge
          cursor="pointer"
          colorScheme={filters.has_classification === true ? "teal" : "gray"}
          onClick={() => toggleFilter("has_classification", true)}
          px="10px" py="4px" borderRadius="8px"
        >
          Classified
        </Badge>
        <Badge
          cursor="pointer"
          colorScheme={filters.has_virustotal_report === true ? "cyan" : "gray"}
          onClick={() => toggleFilter("has_virustotal_report", true)}
          px="10px" py="4px" borderRadius="8px"
        >
          VT Scanned
        </Badge>
        <Badge
          cursor="pointer"
          colorScheme={filters.is_variant === true ? "orange" : "gray"}
          onClick={() => toggleFilter("is_variant", true)}
          px="10px" py="4px" borderRadius="8px"
        >
          Variants Only
        </Badge>
        <Badge
          cursor="pointer"
          colorScheme={filters.is_variant === false ? "blue" : "gray"}
          onClick={() => toggleFilter("is_variant", false)}
          px="10px" py="4px" borderRadius="8px"
        >
          Originals Only
        </Badge>
      </HStack>

      {loading && !data ? (
        <Box textAlign="center" py="40px">
          <Spinner size="xl" color="brand.500" />
        </Box>
      ) : apps.length === 0 ? (
        <Card p="40px" textAlign="center">
          <Icon as={MdAndroid} w="48px" h="48px" color="secondaryGray.400" mb="10px" />
          <Text color={secondaryText}>
            {search || Object.keys(filters).length > 0
              ? "No apps match your search/filters."
              : "No apps analyzed yet. Upload an APK to get started."}
          </Text>
        </Card>
      ) : (
        <>
          <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap="20px">
            {apps.map((app) => (
              <Card
                key={app.app_id}
                p="20px"
                cursor="pointer"
                transition="all 0.2s"
                _hover={{ bg: cardHover, transform: "translateY(-2px)", shadow: "md" }}
                onClick={() => history.push(`/admin/apps/${app.app_id}`)}
              >
                <HStack justify="space-between" align="start">
                  <VStack align="start" spacing="6px" flex={1}>
                    <HStack>
                      <Icon as={MdAndroid} color="green.500" w="20px" h="20px" />
                      <Text fontSize="md" fontWeight="bold" color={textColor} noOfLines={1}>
                        {app.package_name}
                      </Text>
                    </HStack>
                    <HStack spacing="8px" flexWrap="wrap">
                      {app.version_name && (
                        <Badge colorScheme="blue" fontSize="xs">v{app.version_name}</Badge>
                      )}
                      {app.version_code && (
                        <Badge colorScheme="gray" fontSize="xs">code {app.version_code}</Badge>
                      )}
                      {app.is_variant && (
                        <Badge colorScheme="orange" fontSize="xs">variant</Badge>
                      )}
                      {app.has_classification && (
                        <Badge colorScheme="teal" fontSize="xs">Classified</Badge>
                      )}
                      {app.has_virustotal_report && (
                        <Badge colorScheme="cyan" fontSize="xs">
                          <HStack spacing="4px">
                            <Icon as={MdShield} w="10px" h="10px" />
                            <Text>VT Scanned</Text>
                          </HStack>
                        </Badge>
                      )}
                    </HStack>
                    <Text fontSize="xs" color={secondaryText} noOfLines={1}>
                      ID: {app.app_id}
                    </Text>
                  </VStack>
                  <Icon as={MdArrowForward} color={secondaryText} w="18px" h="18px" mt="4px" />
                </HStack>
              </Card>
            ))}
          </SimpleGrid>

          {/* Pagination */}
          {totalPages > 1 && (
            <HStack justify="center" mt="24px" spacing="8px">
              <Button
                size="sm"
                variant="outline"
                isDisabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Text fontSize="sm" color={secondaryText}>
                Page {page} of {totalPages}
              </Text>
              <Button
                size="sm"
                variant="outline"
                isDisabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </HStack>
          )}
        </>
      )}
    </Box>
  );
}
