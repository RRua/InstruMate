import { Box, SimpleGrid } from "@chakra-ui/react";
import React, { useState } from "react";
import ReactDOM from "react-dom";
import Graph from "react-graph-vis";


function randomColor() {
	const red = Math.floor(Math.random() * 256).toString(16).padStart(2, '0');
	const green = Math.floor(Math.random() * 256).toString(16).padStart(2, '0');
	const blue = Math.floor(Math.random() * 256).toString(16).padStart(2, '0');
	return `#${red}${green}${blue}`;
}

class GraphComponent extends React.Component {
	constructor(props) {
		super(props);
		const graph = {
			nodes: [
				{ id: 1, label: "Node 1", title: "node 1 tootip text" },
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
			}
		};
		this.state = {
			graph: graph,
			options: options,
			events: events
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

	render() {
		const { graph, options, events } = this.state;
		return (
			<div>
				<Graph graph={graph} options={options} events={events} style={{ height: "640px" }} />
			</div>
		);
	}
}

export default GraphComponent;