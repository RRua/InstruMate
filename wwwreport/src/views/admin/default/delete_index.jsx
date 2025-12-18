
import {
  Box,
  SimpleGrid,
} from "@chakra-ui/react";
// Assets
// Custom components
import React from "react";
import ComplexTable from "views/admin/default/components/ComplexTable";
import {
  columnsDataComplex,
} from "views/admin/default/variables/columnsData";
import tableDataComplex from "views/admin/default/variables/tableDataComplex.json";
import General from "views/admin/default/components/General"

export default function UserReports() {
  // Chakra Color Mode
  return (
    <Box pt={{ base: "130px", md: "80px", xl: "80px" }}>

      <SimpleGrid columns={{ base: 2, md: 2, xl: 2 }} gap='20px' mb='20px'>
      	<General
          minH='365px'
          pe='20px'
        />
        <ComplexTable
          columnsData={columnsDataComplex}
          tableData={tableDataComplex}
        />
      </SimpleGrid>
    </Box>
  );
}
