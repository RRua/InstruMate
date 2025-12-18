// Chakra imports
import { SimpleGrid, Text } from "@chakra-ui/react";
// Custom components
import Card from "components/card/Card.js";
import React from "react";
import Information from "./Information";



class AppInformation extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			app: {
				"apk_path": "",
				"app_name": "",
				"version_name": "",
				"package_name": "",
				"main_activity": "",
				"dumpsys_main_activity": null,
				"permissions": [],
				"activities": [],
				"md5": "",
				"sha1": "",
				"sha256": "",
				"possible_broadcasts": [
					{
						"event_type": "intent",
						"prefix": "broadcast",
						"action": "android.intent.action.ACTION_POWER_CONNECTED",
						"data_uri": null,
						"mime_type": null,
						"category": null,
						"component": null,
						"flag": null,
						"extra_keys": null,
						"extra_string": null,
						"extra_boolean": null,
						"extra_int": null,
						"extra_long": null,
						"extra_float": null,
						"extra_uri": null,
						"extra_component": null,
						"extra_array_int": null,
						"extra_array_long": null,
						"extra_array_float": null,
						"flags": null,
						"suffix": "",
						"cmd": "am broadcast -a android.intent.action.ACTION_POWER_CONNECTED"
					}
				]
			}
		};
	}

	componentDidMount() {
		fetch('./app.json')
			.then(response => response.json())
			.then(data => this.setState({ app: data }));
	}
	render() {
		const { ...rest } = this.props;
		const { ...app } = this.state.app;
		return (
			<Card mb={{ base: "0px", "2xl": "20px" }} {...rest}>
				<Text
					fontWeight='bold'
					fontSize='2xl'
					mt='10px'
					mb='4px'>
					{app.app_name}
				</Text>
				<Text fontSize='md' me='26px' mb='40px'>
					<p>Version: {app.version_name}</p>
					<p>Main Activity: {app.main_activity}</p>

					<p>Permissions: {app.permissions.length}</p>
					<p>Activities: {app.activities.length}</p>
					<p>Possible Broadcasts: {app.possible_broadcasts.length}</p>

					<p>MD5: {app.md5}</p>
					<p>SHA1: {app.sha1}</p>
					<p>SHA256: {app.sha256}</p>
				</Text>
			</Card>
		);
	}
}

export default AppInformation;
