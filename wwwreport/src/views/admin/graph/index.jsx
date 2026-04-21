import React, { useState, useEffect } from "react";
import {
  Box,
  Text,
  Spinner,
  Input,
  InputGroup,
  InputLeftElement,
  HStack,
  Button,
  Icon,
  useColorModeValue,
  Select,
} from "@chakra-ui/react";
import { MdSearch, MdArrowBack } from "react-icons/md";
import { useHistory, useParams } from "react-router-dom";
import Card from "components/card/Card";
import GraphWrapperComponent from "./components/GraphWrapper";
import { getCallGraph } from "api";

export default function CallGraphView() {
  const { appId } = useParams();
  const history = useHistory();
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterInput, setFilterInput] = useState("");
  const [filter, setFilter] = useState("");
  const [limit, setLimit] = useState(500);
  const [totalNodes, setTotalNodes] = useState(0);
  const [totalEdges, setTotalEdges] = useState(0);

  const textColor = useColorModeValue("secondaryGray.900", "white");
  const secondaryText = useColorModeValue("secondaryGray.600", "secondaryGray.500");

  useEffect(() => {
    setLoading(true);
    getCallGraph(appId, limit, filter)
      .then((data) => {
        setGraphData({ nodes: data.nodes, edges: data.edges });
        setTotalNodes(data.total_nodes);
        setTotalEdges(data.total_edges);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [appId, limit, filter]);

  // Debounced filter
  useEffect(() => {
    const timer = setTimeout(() => setFilter(filterInput), 400);
    return () => clearTimeout(timer);
  }, [filterInput]);

  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
      <HStack mb="16px" spacing="12px" flexWrap="wrap">
        <Button
          size="sm"
          leftIcon={<MdArrowBack />}
          variant="outline"
          onClick={() => history.push(`/admin/apps/${appId}`)}
        >
          Back to App
        </Button>
        <Text fontSize="2xl" fontWeight="bold" color={textColor}>
          Call Graph
        </Text>
        <Text fontSize="sm" color={secondaryText}>
          {totalNodes} nodes, {totalEdges} edges
        </Text>
      </HStack>

      <Card p="16px" mb="16px">
        <HStack spacing="12px" flexWrap="wrap">
          <InputGroup maxW="300px">
            <InputLeftElement pointerEvents="none">
              <Icon as={MdSearch} color="secondaryGray.400" />
            </InputLeftElement>
            <Input
              placeholder="Filter nodes..."
              value={filterInput}
              onChange={(e) => setFilterInput(e.target.value)}
              size="md"
              borderRadius="12px"
            />
          </InputGroup>
          <Select
            maxW="150px"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            size="md"
            borderRadius="12px"
          >
            <option value={100}>100 nodes</option>
            <option value={500}>500 nodes</option>
            <option value={1000}>1000 nodes</option>
            <option value={5000}>5000 nodes</option>
            <option value={10000}>10000 nodes</option>
          </Select>
          {graphData && (
            <Text fontSize="sm" color={secondaryText}>
              Showing {graphData.nodes.length} nodes, {graphData.edges.length} edges
            </Text>
          )}
        </HStack>
      </Card>

      {loading ? (
        <Box textAlign="center" py="60px">
          <Spinner size="xl" color="brand.500" />
          <Text mt="12px" color={secondaryText}>Loading call graph...</Text>
        </Box>
      ) : error ? (
        <Card p="30px">
          <Text color="red.500">{error}</Text>
        </Card>
      ) : graphData ? (
        <Card p="0" overflow="hidden">
          <GraphWrapperComponent graphData={graphData} />
        </Card>
      ) : null}
    </Box>
  );
}
