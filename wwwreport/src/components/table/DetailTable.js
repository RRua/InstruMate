/*Based on 
https://codesandbox.io/p/sandbox/complete-react-table-with-filter-sorting-and-pagination-gjxt6?file=%2Fsrc%2FApp.js%3A4%2C1-4%2C38
*/
import React, { useState } from "react";
import ReactDOM from "react-dom";
import VisGraph, {
	GraphData,
	GraphEvents,
	Options,
} from 'react-vis-graph-wrapper';
import {
	Button,
	Modal,
	ModalOverlay,
	ModalContent,
	ModalHeader,
	ModalFooter,
	ModalBody,
	ModalCloseButton,
	Box,
	Image,
	SimpleGrid,
	Grid,
	GridItem,
	AspectRatio,
	Text,
	List,
	ListItem,
	Input,
} from '@chakra-ui/react'
import Card from "components/card/Card.js";

import {
	Table,
	Thead,
	Tbody,
	Tfoot,
	Tr,
	Th,
	Td,
	TableCaption,
	TableContainer,
} from '@chakra-ui/react'

class DetailTable extends React.Component {
	constructor(props) {
		super(props);
		let { tableData, useKeysAsColumns } = this.props;
		let columnNames = [];
		let columnData = [];
		if (tableData != null && tableData.length > 0) {
			if (useKeysAsColumns) {
				columnNames = Object.keys(tableData[0]);
				for (var i = 0; i < tableData.length; i++) {
					let row = [];
					for (var j = 0; j < columnNames.length; j++) {
						console.log(columnNames[j]);
						console.log(tableData[columnNames[j]]);
						row.push(tableData[i][columnNames[j]]);
					}
					columnData.push(row);
				}
			} else {
				if (tableData[0] != null) {
					if (typeof tableData[0] === "string") {
						columnNames = ["Value"];
						for (var i = 0; i < tableData.length; i++) {
							let row = [tableData[i]];
							columnData.push(row);
						}

					} else if (Array.isArray(tableData[0])) {
						for (var i = 0; i < tableData[0].length; i++) {
							columnNames.push("Value " + i);
						}
						columnData.push(...tableData);
					}
				}
			}
		}
		this.state = {
			originalData: columnData,
			columnNames: columnNames,
			columnData: columnData,
			searchInput: ""
		};
	}

	componentDidMount() {
	}

	handleChange = event => {
		this.setState({ searchInput: event.target.value }, () => {
			this.globalSearch();
		});
	};

	globalSearch = () => {
		let { searchInput, originalData } = this.state;
		let filteredData = originalData.filter(value => {
			let filteredColumns = value.filter(colValue => {
				return colValue.toLowerCase().includes(searchInput.toLowerCase())
			});
			return (filteredColumns.length > 0);
		});
		this.setState({ columnData: filteredData });
	};

	render() {
		let { columnNames, columnData, searchInput } = this.state;
		console.log(columnNames);
		console.log(columnData);
		return (
			<Box overflowX="scroll" minH="400px" maxH="400px" minW="800px" maxW="800px">
				<Grid>
					<GridItem>
						<Input placeholder='Search'
							value={searchInput || ""}
							onChange={this.handleChange} />
					</GridItem>
					<GridItem>
						<Table variant="simple" size="sm">
							<Thead>
								<Tr>
									{columnNames.map((item, index) => (
										<Th key={"th_" + index}>{item}</Th>
									))}
								</Tr>
							</Thead>
							<Tbody>
								{columnData.map((row, index) => (
									<Tr key={"tr_" + index}>
										{row.map((rowItem, rowIndex) => (
											<Td key={"td_" + index + "_" + rowIndex}>{rowItem}</Td>
										))}
									</Tr>
								))}
							</Tbody>
						</Table>
					</GridItem>
				</Grid>
			</Box>
		);
	}
}

export default DetailTable;