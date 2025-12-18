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
import DetailTable from "components/table/DetailTable";

class GraphWrapperComponent extends React.Component {
	constructor(props) {
		super(props);
		const graph = {
			nodes: [
				{ id: 1, label: "Node 1 --", title: "node 1 tootip text", image: "./states/START.png" },
				{ id: 2, label: "Node 2", title: "node 2 tootip text" },
				{ id: 3, label: "Node 3", title: "node 3 tootip text" },
				{ id: 4, label: "Node 4", title: "node 4 tootip text" },
				{ id: 5, label: "Node 5", title: "node 5 tootip text" }
			],
			edges: [
				{ from: 1, to: 2 },
				{ from: 1, to: 3 },
				{ from: 2, to: 4 },
				{ from: 2, to: 5 }
			]
		};

		const options = {
			autoResize: true,
			height: '100%',
			width: '100%',
			locale: 'en',

			nodes: {
				shapeProperties: {
					useBorderWithImage: true
				},

				borderWidth: 0,
				borderWidthSelected: 5,

				color: {
					border: '#FFFFFF',
					background: '#FFFFFF',

					highlight: {
						border: '#0000FF',
						background: '#0000FF',
					}
				},

				font: {
					size: 12,
					color: '#000'
				}
			},
			edges: {
				color: 'black',
				arrows: {
					to: {
						enabled: true,
						scaleFactor: 0.5
					}
				},
				font: {
					size: 12,
					color: '#000'
				}
			}
		};

		const events = {
			select: function(event) {
				var { nodes, edges } = event;
				console.log(nodes);
				this.setState({
					...this.state,
					showModal: true
				});
			}
		};
		var selectedNode = {
			"signature": "00cddfd42b8664f2e9f5a82b96a4367b",
			"snapshot": "ViewState_c684c65ec7a5c7db6d66074c02d71cbf_Snapshot.png",
			"top_activity": "com.whatsapp/.support.DescribeProblemActivity",
			"action_units": [
				{
					"view_id": "id/no_id/2",
					"cls": "android.widget.ImageButton",
					"pkg": "com.whatsapp",
					"label": "Navigate up",
					"type": "tap"
				},
			],
			"activity_stack": [],
			"sensitive_apis": [],
			"class_modules": [],
			"native_modules": [],
			"private_dir_files": [],
			"shared_dir_files": [],
			"id": "00cddfd42b8664f2e9f5a82b96a4367b",
			"image": "./states/ViewState_c684c65ec7a5c7db6d66074c02d71cbf_Snapshot.png",
			"label": "00cddfd42b8664f2e9f5a82b96a4367b",
			"shape": "image"
		};

		this.state = {
			graph: graph,
			options: options,
			events: events,
			selectedNode: selectedNode,
		};
	}

	componentDidMount() {
		fetch('./graph-vis.json')
			.then(response => response.json())
			.then(data => this.setState({
				...this.state,
				graph: data
			}));
	}

	_openNodeDialog = (selectedNodeId) => {
		var nodes = this.state.graph.nodes;
		var selectedNode = null;
		for (var i = 0; i < nodes.length; i++) {
			if (nodes[i].id == selectedNodeId) {
				selectedNode = nodes[i];
			}
		}
		this.setState({ showModal: true, selectedNode: selectedNode });
	};

	_closeNodeDialog = () => {
		this.setState({ showModal: false });
	}

	_openTableModal = (tableData, tableTitle, useKeysAsColumns) => {
		this.setState({ showTableModal: true, tableData: tableData, tableTitle: tableTitle, useKeysAsColumns: useKeysAsColumns });
	}

	_closeTableModal = () => {
		this.setState({ showTableModal: false });
	}

	render() {
		const { graph, options, events, selectedNode } = this.state;
		let containerStyle = {  //define container width and height.
			width: "800px",
			height: "800px",
		}
		const { showModal, showTableModal, tableData, tableTitle, useKeysAsColumns } = this.state;
		return (
			<div style={containerStyle}>
				<VisGraph
					graph={graph}
					options={options}
					events={{
						selectNode: (event) => {
							var { nodes, edges } = event;
							if (nodes.length == 1) {
								this._openNodeDialog(nodes[0]);
							}
						}
					}}
					ref={(network) => {
						//  if you want access to vis.js network api you can set the state in a parent component using this property
						console.log(network);
					}}
				/>
				<Modal isOpen={showModal} onClose={this._closeNodeDialog} size="md">
					<ModalOverlay />
					<ModalContent
						minWidth="fit-content"
						height="fit-content">
						<ModalHeader>{selectedNode.label}</ModalHeader>
						<ModalCloseButton />
						<ModalBody>
							<Grid templateColumns='repeat(3, 1fr)'>
								<GridItem>
									<Image maxWidth="200px" src={selectedNode.image} />
								</GridItem>
								<GridItem colSpan={2}>
									<TableContainer>
										<Table size="sm">
											<Tbody>
												<Tr>
													<Td>ID</Td>
													<Td>{selectedNode.id}</Td>
												</Tr>
												<Tr>
													<Td>Snapshot</Td>
													<Td>{selectedNode.snapshot}</Td>
												</Tr>
												<Tr>
													<Td>Top Activity</Td>
													<Td>{selectedNode.top_activity}</Td>
												</Tr>
												<Tr>
													<Td>Activity Stack</Td>
													<Td>
														<List styleType="none">
															{selectedNode.activity_stack.map((item, index) => (
																<ListItem key={index}>{item}</ListItem>
															))}
														</List>
													</Td>
												</Tr>
												<Tr>
													<Td>Private dir files</Td>
													<Td>
														<Box overflowX="scroll" maxH="150px" maxW="400px">
															<List styleType="none">
																{selectedNode.private_dir_files.map((item, index) => (
																	<ListItem key={index}>{item}</ListItem>
																))}
															</List>
														</Box>
													</Td>
												</Tr>
												<Tr>
													<Td>Shared dir files</Td>
													<Td>
														<Box overflowX="scroll" maxH="150px" maxW="400px">
															<List styleType="none">
																{selectedNode.shared_dir_files.map((item, index) => (
																	<ListItem key={index}>{item}</ListItem>
																))}
															</List>
														</Box>
													</Td>
												</Tr>
												<Tr>
													<Td>UI Components</Td>
													<Td>{selectedNode.action_units.length}</Td>
												</Tr>
												<Tr>
													<Td>Sensitive APIs</Td>
													<Td>{selectedNode.sensitive_apis.length}</Td>
												</Tr>
												<Tr>
													<Td>Native Modules</Td>
													<Td>{selectedNode.native_modules.length}</Td>
												</Tr>
												<Tr>
													<Td>Class Modules</Td>
													<Td>{selectedNode.class_modules.length}</Td>
												</Tr>
											</Tbody>
										</Table>
									</TableContainer>
								</GridItem>
							</Grid>
						</ModalBody>

						<ModalFooter>
							<Button colorScheme='red' mr={3}>
								Close
							</Button>
							<Button colorScheme='blue' mr={3}
								onClick={() => { this._openTableModal(selectedNode.action_units, 'UI Components', true); }}>
								UI Components
							</Button>
							<Button colorScheme='blue' mr={3}
								onClick={() => { this._openTableModal(selectedNode.sensitive_apis, 'Sensitive APIs', false); }}>
								Sensitive APIs
							</Button>
							<Button colorScheme='blue' mr={3}
								onClick={() => { this._openTableModal(selectedNode.native_modules, 'Native Modules', false); }}>
								Native Modules
							</Button>
							<Button colorScheme='blue'
								onClick={() => { this._openTableModal(selectedNode.class_modules, 'Class Modules', false); }}>
								Class Modules
							</Button>
						</ModalFooter>
					</ModalContent>
				</Modal>
				<Modal isOpen={showTableModal} onClose={this._closeTableModal} size="md">
					<ModalOverlay />
					<ModalContent
						minWidth="fit-content"
						height="fit-content">
						<ModalHeader>{tableTitle}</ModalHeader>
						<ModalCloseButton />
						<ModalBody>
							<DetailTable tableData={tableData} useKeysAsColumns={useKeysAsColumns} />
						</ModalBody>

						<ModalFooter>
							<Button colorScheme='blue' mr={3} onClick={this._closeTableModal}>
								Close
							</Button>
							<Button variant='ghost'>Secondary Action</Button>
						</ModalFooter>
					</ModalContent>
				</Modal>
			</div>
		);
	}
}

export default GraphWrapperComponent;