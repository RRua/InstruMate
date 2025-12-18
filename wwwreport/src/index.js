import React from 'react';
import ReactDOM from 'react-dom';
import 'assets/css/App.css';
import { HashRouter, Route, Switch, Redirect } from 'react-router-dom';
import AdminLayout from 'layouts/admin';
import { ChakraProvider } from '@chakra-ui/react';
import theme from 'theme/theme';
import { ThemeEditorProvider } from '@hypertheme-editor/chakra-ui';

ReactDOM.render(
	<ChakraProvider theme={theme}>
		<ThemeEditorProvider>
			<HashRouter>
				<Switch>
					<Route path={`/admin`} component={AdminLayout} />
					<Redirect from='/' to='/admin' />
				</Switch>
			</HashRouter>
		</ThemeEditorProvider>
	</ChakraProvider>,
	document.getElementById('root')
);
