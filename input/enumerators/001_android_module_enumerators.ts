const module_enumerators_start = Date.now();
const CLASS_MODULE = "class_module";
const NATIVE_MODULE_EXPORTS = "native_module_exports";
const NATIVE_MODULES = "native_module";
const ME_DEBUG = "DEBUG";
const ME_INFO = "INFO";

function ModuleEnumerators_send_message(module_type: any, module_name: any,
	module_base: any, module_size: any, module_path: any,
	export_name: any, export_type: any, export_address: any) {
	let message_content = {
		timestamp: Date.now() - module_enumerators_start,
		module_type: module_type,
		module_name: module_name,
		module_base: module_base,
		module_size: module_size,
		module_path: module_path,
		export_name: export_name,
		export_type: export_type,
		export_address: export_address
	};
	let message = { message: message_content, messageType: 'MODULE_ENUMERATION' };
	// @ts-ignore
	send(message, null);
}

function ModuleEnumerators_send_debug_msg(txt_message: string, txt_level: string) {
	let message_internal = {message: txt_message, level: txt_level};
	let message = { message: message_internal, messageType: 'INTERNAL_LOGGING' };
	//console.log("Missed return value of type: "+class_signature);
	// @ts-ignore
	send(message, null);
}

function enumerate_classes() {
	// @ts-ignore
	Java.perform(() => {
		let selector = {
			onMatch: (className: any) => {
				let module_type = CLASS_MODULE;
				let module_name = className;
				let module_base = null;
				let module_size = null;
				let module_path = null;
				let export_name = null;
				let export_type = null;
				let export_address = null;
				ModuleEnumerators_send_message(module_type, module_name,
					module_base, module_size, module_path,
					export_name, export_type, export_address);
			},
			onComplete: () => {
				//console.log('java_class_loader enumerator finished');
			}
		}
		// @ts-ignore
		Java.enumerateLoadedClasses(selector)
		ModuleEnumerators_send_debug_msg("Enumeration: observing loaded classes", ME_INFO);
	});

	setTimeout(enumerate_classes, 5000);
}

function enumerate_native_modules_with_exports() {
	// @ts-ignore
	Java.perform(() => {
		let selector = {
			onMatch: function(mm: any) {
				// @ts-ignore
				Module.enumerateExports(mm.name, {
					onMatch: function(exp: any) {
						let module_type = NATIVE_MODULE_EXPORTS;
						let module_name = mm.name;
						let module_base = mm.base;
						let module_size = mm.size;
						let module_path = mm.path;
						let export_name = exp.name;
						let export_type = exp.type;
						let export_address = exp.address;
						ModuleEnumerators_send_message(module_type, module_name,
							module_base, module_size, module_path,
							export_name, export_type, export_address);
					},
					onComplete: function() { }
				});
			},
			onComplete: function() {
			}
		}
		// @ts-ignore
		Process.enumerateModules(selector);
		ModuleEnumerators_send_debug_msg("Enumeration: observing modules and its exports", ME_INFO);
	});
	//setTimeout(enumerate_native_modules, 10000);
}

function enumerate_native_modules_without_exports() {
	// @ts-ignore
	Java.perform(() => {
		let selector = {
			onMatch: function(mm: any) {
				let module_type = NATIVE_MODULE_EXPORTS;
				let module_name = mm.name;
				let module_base = mm.base;
				let module_size = mm.size;
				let module_path = mm.path;
				let export_name = null;
				let export_type = null;
				let export_address = null;
				ModuleEnumerators_send_message(module_type, module_name,
					module_base, module_size, module_path,
					export_name, export_type, export_address);
			},
			onComplete: function() {
			}
		}
		// @ts-ignore
		Process.enumerateModules(selector);
		ModuleEnumerators_send_debug_msg("Enumeration: observing modules", ME_INFO);
	});
	setTimeout(enumerate_native_modules_without_exports, 5000);
}

setTimeout(enumerate_classes, 1000);
setTimeout(enumerate_native_modules_with_exports, 2000);
setTimeout(enumerate_native_modules_without_exports, 5000);

