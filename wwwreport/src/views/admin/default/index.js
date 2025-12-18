import React from "react";
import {
	Box,
	SimpleGrid,
} from "@chakra-ui/react";
import AppInformation from "views/admin/default/components/AppInformation"

class MainReport extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	componentDidMount() {
		fetch('./app.json')
        	.then(response => response.json())
        	.then(data => this.setState({ app: data }));
	}

	render() {
		return (
			<Box pt={{ base: "130px", md: "80px", xl: "80px" }}>
				<SimpleGrid columns={{ base: 1, md: 1, xl: 1 }} gap='20px' mb='20px'>
					<AppInformation
						minH='365px'
						pe='20px'
					/>
				</SimpleGrid>
			</Box>
		);
	}
}

export default MainReport;