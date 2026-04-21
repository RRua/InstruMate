import React from "react";
import VisGraph from 'react-vis-graph-wrapper';
import { Box } from '@chakra-ui/react';

const defaultOptions = {
	autoResize: true,
	height: '100%',
	width: '100%',
	locale: 'en',
	physics: {
		stabilization: { iterations: 100 },
		barnesHut: { gravitationalConstant: -2000, springLength: 150 },
	},
	nodes: {
		shape: 'dot',
		size: 10,
		borderWidth: 1,
		borderWidthSelected: 3,
		color: {
			border: '#4A90D9',
			background: '#5BA8F5',
			highlight: {
				border: '#0000FF',
				background: '#4444FF',
			}
		},
		font: {
			size: 10,
			color: '#333',
			face: 'monospace',
		}
	},
	edges: {
		color: { color: '#999', highlight: '#333' },
		arrows: {
			to: { enabled: true, scaleFactor: 0.4 }
		},
		smooth: { type: 'continuous' },
	},
	interaction: {
		hover: true,
		tooltipDelay: 200,
		zoomView: true,
		dragView: true,
	},
	layout: {
		improvedLayout: true,
	},
};

class GraphWrapperComponent extends React.Component {
	render() {
		const { graphData } = this.props;
		if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
			return (
				<Box p="40px" textAlign="center" color="gray.500">
					No graph data to display.
				</Box>
			);
		}

		return (
			<Box style={{ width: "100%", height: "700px" }}>
				<VisGraph
					graph={graphData}
					options={defaultOptions}
					events={{}}
				/>
			</Box>
		);
	}
}

export default GraphWrapperComponent;
