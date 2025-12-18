const start = Date.now();
const INFO = "INFO";
const DEBUG = "DEBUG";

function Java_send_message(java_signature: string, qualifier: string, reason:string, argumentValues: any, returnedVal:any) {
	let message_content = {
		timestamp: Date.now() - start,
		java_signature: java_signature,
		qualifier: qualifier,
		reason: reason,
		argumentValues: argumentValues,
		returnedVal: returnedVal,
		data_type: 'stack_trace',
		data: ''
	};
	// @ts-ignore
	let Log = Java.use("android.util.Log");
	// @ts-ignore
	let newException = Java.use("java.lang.Exception").$new();
	let data = Log.getStackTraceString(newException);
	message_content.data = data;
	let message = { message: message_content, messageType: 'JAVA_METHOD_INTERCEPTED' };
	//console.log(JSON.stringify(message_content));
	// @ts-ignore
	send(message, null);
}

function Java_send_debug_msg(txt_message: string, txt_level: string){
	let message_internal = {message: txt_message, level: txt_level};
	let message = { message: message_internal, messageType: 'INTERNAL_LOGGING' };
	//console.log("Missed return value of type: "+class_signature);
	// @ts-ignore
	send(message, null);
}

function Java_to_string(class_signature:string, value: any){
	try{
		switch(class_signature) {
			case "java.lang.String":
			case "long":
			case "float":
			case "int":
			case "double":
			case "boolean":
			case "byte":
				return value+"";
			case "boolean[]":
			case "byte[]":
			case "long[]":
			case "int[]":
			case "android.net.Network[]":
			case "java.lang.Object[]":
			case "java.net.URL[]":
			case "java.lang.String[]":
				if(value) {
					let retVal = "";
					for(let i = 0; i < value.length; i++){
						if( i>0 ) {
							retVal = retVal+",";
						}
						retVal = retVal + value[i];
					}
					return retVal;
				}else{
					return "";
				}
			case "void":
				return "";
			case "java.io.File":
				// @ts-ignore
				let clazzFile = Java.use("java.io.File");
				// @ts-ignore
				let file = Java.cast(value, clazzFile);
				let filepath = file.getAbsolutePath();
				return filepath;
			case "java.io.FileDescriptor":
				// @ts-ignore
				let clazzFD = Java.use("java.io.FileDescriptor");
				// @ts-ignore
				let fileDescriptor = Java.cast(value, clazzFD);
				let fdID = "FD-" + fileDescriptor.hashCode();
				return fdID;
			case "android.content.ContentValues":
				// @ts-ignore
				let clazzCV = Java.use("android.content.ContentValues");
				// @ts-ignore
				let contentValues = Java.cast(value, clazzCV);
				return contentValues.toString();
			case "java.util.Locale":
				return value+"";
			case "android.content.ComponentName":
				// @ts-ignore
				let clazzCompName = Java.use("android.content.ComponentName");
				// @ts-ignore
				let objCompName = Java.cast(value, clazzCompName);
				return objCompName.flattenToString();
			case "android.os.Bundle":
				return value+"";
			case "android.content.pm.PackageInfo":
				return value+"";
			case "java.lang.Class":
				return value+"";
			case "java.lang.Object":
				return value+"";
			case "android.net.NetworkInfo":
				return value+"";
			case "android.view.accessibility.AccessibilityEvent":
				return value+"";
			case "android.app.NotificationChannel":
				return value+"";
			case "android.net.LinkProperties":
				return value+"";
			case "java.net.URL":
				return value+"";
			case "okhttp3.HttpUrl":
				return value+"";
			case "okhttp3.RequestBody":
				return value+"";
			case "okhttp3.ResponseBody":
				return value+"";
			case "okhttp3.Request":
				return value+"";
			case "okhttp3.OkHttpClient$Builder":
			case "okhttp3.Call":
				return "";
			default:
				Java_send_debug_msg("Missed return value of type: "+class_signature, DEBUG)
				return "";
		}
	}catch(e){
		console.log('Error at '+class_signature);
		console.log(e);
		return e+"";
	}
}

// @ts-ignore
Java.perform(function() {
	let INTERCEPTORS = [
<#list items as intercept>
		{
		   clazz: '${intercept.clazz}',
		   enabled: ${intercept.enabled?c},
		   signature: '${intercept.signature}',
		   debug_overload: "clazz.${intercept.methodName}.overload(${intercept.jsOverload})",
		   fn_intercept: (clazz: any, method_signature: string) => {
		       let method = clazz.${intercept.methodName}.overload(${intercept.jsOverload});
		       method.implementation = function(${intercept.jsImplementation}) {
		           let returnVal = method.call(this, ${intercept.jsArgsForCall});
		           let argumentValues = {
		               <#list intercept.arguments as argumentValue, argumentType>
    				   "${argumentValue}": Java_to_string("${argumentType}", ${argumentValue}),
					   </#list> 
		           };
		           let returnedVal = {
		               "callResult": Java_to_string("${intercept.returnType}", returnVal)
		           };
		           Java_send_message(method_signature, "${intercept.qualifier}", "${intercept.reason}", argumentValues, returnedVal);
		           return returnVal;
		       }
		   }
		},
</#list>
	];
	
	let failedCount = 0;
	for (let i = 0; i < INTERCEPTORS.length; i++) {
		let interceptor = INTERCEPTORS[i];
		if (interceptor.enabled) {
			let clazz = null;
			try {
				// @ts-ignore
				clazz = Java.use(interceptor.clazz);
			}catch(e){
				Java_send_debug_msg("Class not found "+interceptor.clazz, DEBUG);
			}
			if (clazz) {
				try{
					interceptor.fn_intercept(clazz, interceptor.signature);
				}catch(e){
					Java_send_debug_msg("Error intercepting: "+interceptor.signature, DEBUG);
					//console.log("Error intercepting: "+interceptor.signature);
					//console.log("Debug info: "+interceptor.debug_overload);
					//console.log(e);
					failedCount++;
				}
			} else {
				Java_send_debug_msg("Could not intercept: " + interceptor.signature, DEBUG);
				//console.log("Could not intercept: " + interceptor.signature);
				failedCount++;
			}
		}
	}
	console.log("Interceptors: "+INTERCEPTORS.length);
	console.log("Failed: "+failedCount);
	console.log("Success: "+(INTERCEPTORS.length-failedCount));

});