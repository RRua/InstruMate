package com.forensicmate.analysis;

import java.util.LinkedList;
import java.util.List;

public class ClassBagBuilder {

	private static boolean captureParcelSmallIO = false;
	private static boolean captureParcelBigIO = true;

	@SuppressWarnings("deprecation")
	private static IClassBag buildGeoApi() {
		GenericClassBag bag = new GenericClassBag();
		bag.setName("GEOAPI");
		bag.getClazzes().add(com.google.android.gms.maps.GoogleMap.class.getName());
		bag.getArguments().add(com.google.android.gms.maps.GoogleMap.OnMyLocationButtonClickListener.class.getName());
		bag.getArguments().add(com.google.android.gms.maps.GoogleMap.OnMapClickListener.class.getName());
		bag.getArguments().add(com.google.android.gms.maps.GoogleMap.OnCameraChangeListener.class.getName());
		bag.getArguments().add(com.google.android.gms.maps.GoogleMap.OnCameraMoveListener.class.getName());

		bag.getClazzes().add(android.location.LocationManager.class.getName());
		bag.getReturns().add(android.location.Location.class.getName());
		bag.getArguments().add(android.location.LocationListener.class.getName());
		bag.getArguments().add(android.location.GpsStatus.NmeaListener.class.getName());
		bag.getArguments().add(android.location.GpsStatus.Listener.class.getName());
		return bag;
	}

	private static IClassBag buildFileApi() {
		GenericClassBag bag = new GenericClassBag();
		bag.setName("IO");
		bag.getClazzes().add(java.io.File.class.getName());
		bag.getClazzes().add(java.io.FileInputStream.class.getName());
		bag.getClazzes().add(java.io.FileOutputStream.class.getName());
		bag.getArguments().add(java.io.File.class.getName());
		bag.getArguments().add(java.io.FileDescriptor.class.getName());
		bag.getReturns().add(java.io.File.class.getName());
		bag.getReturns().add(java.io.FileDescriptor.class.getName());
		return bag;
	}

	public static IClassBag buildSqliteDatabaseApiBag() {
		GenericClassBag bag1 = new GenericClassBag();
		bag1.setName("SQLiteDatabase");
		bag1.getClazzes().add(android.database.sqlite.SQLiteDatabase.class.getName());
		bag1.getMethodNames().add("create");
		bag1.getMethodNames().add("delete");
		bag1.getMethodNames().add("execSQL");
		bag1.getMethodNames().add("getPath");
		bag1.getMethodNames().add("insert");
		bag1.getMethodNames().add("insertOrThrow");
		bag1.getMethodNames().add("insertWithOnConflict");
		bag1.getMethodNames().add("isOpen");
		bag1.getMethodNames().add("isReadOnly");
		bag1.getMethodNames().add("openDatabase");
		bag1.getMethodNames().add("openOrCreateDatabase");
		bag1.getMethodNames().add("query");
		bag1.getMethodNames().add("rawQuery");
		bag1.getMethodNames().add("rawQueryWithFactory");
		bag1.getMethodNames().add("replace");
		bag1.getMethodNames().add("replaceOrThrow");
		bag1.getMethodNames().add("setLocale");
		bag1.getMethodNames().add("getLocale");
		bag1.getMethodNames().add("update");
		bag1.getMethodNames().add("updateWithOnConflict");
		return bag1;
	}

	public static IClassBag buildHardwareBag() {
		GenericClassBag bag = new GenericClassBag();
		bag.setName("Hardware");
		bag.getClazzes().add(android.hardware.Camera.class.getName());
		bag.getClazzes().add(android.hardware.GeomagneticField.class.getName());
		bag.getClazzes().add(android.hardware.Sensor.class.getName());
		bag.getClazzes().add(android.hardware.SensorEvent.class.getName());
		bag.getClazzes().add(android.hardware.SensorManager.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbDevice.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbAccessory.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbDeviceConnection.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbRequest.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbInterface.class.getName());
		bag.getClazzes().add(android.hardware.usb.UsbEndpoint.class.getName());
		bag.getClazzes().add(android.hardware.input.InputManager.class.getName());
		bag.setAllClassMethods(true);
		return bag;
	}

	//just test
	/*
	private IClassBag buildIPCGenericBag() {
		GenericClassBag intentBags1 = new GenericClassBag();
		intentBags1.getClazzes().add(android.content.Intent.class.getName());
		intentBags1.getClazzes().add(android.content.IntentSender.class.getName());
		intentBags1.getClazzes().add(android.content.IntentFilter.class.getName());
		intentBags1.getClazzes().add(android.app.PendingIntent.class.getName());
		intentBags1.getClazzes().add(android.content.BroadcastReceiver.class.getName());
		intentBags1.getClazzes().add(android.content.ContentResolver.class.getName());
		intentBags1.setAllClassMethods(true);

		intentBag2.getClazzes().add(android.content.Context.class.getName());
		intentBag2.getArguments().add(android.content.Intent.class.getName());
		intentBag2.getReturns().add(android.content.Intent.class.getName());
		intentBag2.getArguments().add(android.content.BroadcastReceiver.class.getName());
		intentBag2.getReturns().add(android.content.BroadcastReceiver.class.getName());
		
		GenericClassBag parcelBag = new GenericClassBag();
		parcelBag.setName("Parcel");
		parcelBag.getClazzes().add(android.os.Parcel.class.getName());
		parcelBag.getExcludedMethodNames().add("readParcelableCreator");
		parcelBag.getExcludedMethodNames().add("recycle");
		parcelBag.setAllClassMethods(true);

		MultipleClassBag multiBag = new MultipleClassBag("IPC", intentBags1, intentBag2);
		return multiBag;
	}*/

	public static IClassBag buildIPCIntents() {
		/*GenericClassBag ipcIntent1 = new GenericClassBag();
		ipcIntent1.setName("IPC-Ctx-Intent");
		ipcIntent1.getClazzes().add(android.content.Context.class.getName());
		ipcIntent1.getMethodNames().add("registerReceiver");
		ipcIntent1.getMethodNames().add("removeStickyBroadcast");
		ipcIntent1.getMethodNames().add("removeStickyBroadcastAsUser");
		ipcIntent1.getMethodNames().add("sendBroadcast");
		ipcIntent1.getMethodNames().add("sendBroadcastAsUser");
		ipcIntent1.getMethodNames().add("sendBroadcastWithMultiplePermissions");
		ipcIntent1.getMethodNames().add("sendOrderedBroadcast");
		ipcIntent1.getMethodNames().add("sendOrderedBroadcastAsUser");
		ipcIntent1.getMethodNames().add("sendStickyBroadcast");
		ipcIntent1.getMethodNames().add("sendStickyBroadcastAsUser");
		ipcIntent1.getMethodNames().add("sendStickyOrderedBroadcast");
		ipcIntent1.getMethodNames().add("sendStickyOrderedBroadcastAsUser");*/

		GenericClassBag ipcPendingIntent = new GenericClassBag();
		ipcPendingIntent.setName("IPC-PendingIntent");
		ipcPendingIntent.getClazzes().add(android.app.PendingIntent.class.getName());
		ipcPendingIntent.getMethodNames().add("cancel");
		ipcPendingIntent.getMethodNames().add("send");
		ipcPendingIntent.getMethodNames().add("writeToParcel");

		GenericClassBag intentCreation = new GenericClassBag();
		intentCreation.setName("IPC-Intent");
		intentCreation.getClazzes().add(android.content.Intent.class.getName());
		intentCreation.getArguments().add(java.lang.String.class.getName());
		intentCreation.getReturns().add(java.lang.String.class.getName());
		intentCreation.getArguments().add(android.os.Bundle.class.getName());
		intentCreation.getReturns().add(android.os.Bundle.class.getName());
		intentCreation.getArguments().add(android.os.Parcel.class.getName());
		intentCreation.getReturns().add(android.os.Parcel.class.getName());

		GenericClassBag parcelBag = new GenericClassBag();
		parcelBag.setName("IPC-Parcel");
		parcelBag.getClazzes().add(android.os.Parcel.class.getName());
		parcelBag.getMethodNames().add("<init>");
		parcelBag.getExcludedMethodNames().add("readParcelableCreator");
		parcelBag.getExcludedMethodNames().add("recycle");
		parcelBag.getExcludedMethodNames().add("obtain");
		parcelBag.getExcludedMethodNames().add("writeInterfaceToken");
		if (captureParcelSmallIO) {
			parcelBag.getMethodNames().add("createBooleanArray");
			parcelBag.getMethodNames().add("createByteArray");
			parcelBag.getMethodNames().add("createCharArray");
			parcelBag.getMethodNames().add("createDoubleArray");
			parcelBag.getMethodNames().add("createFloatArray");
			parcelBag.getMethodNames().add("createIntArray");
			parcelBag.getMethodNames().add("createLongArray");
			parcelBag.getMethodNames().add("createStringArray");
			parcelBag.getMethodNames().add("readBooleanArray");
			parcelBag.getMethodNames().add("readByte");
			parcelBag.getMethodNames().add("readByteArray");
			parcelBag.getMethodNames().add("readCharArray");
			parcelBag.getMethodNames().add("readDouble");
			parcelBag.getMethodNames().add("readDoubleArray");
			parcelBag.getMethodNames().add("readFloat");
			parcelBag.getMethodNames().add("readFloatArray");
			parcelBag.getMethodNames().add("readInt");
			parcelBag.getMethodNames().add("readIntArray");
			parcelBag.getMethodNames().add("readLong");
			parcelBag.getMethodNames().add("readLongArray");
			parcelBag.getMethodNames().add("writeBooleanArray");
			parcelBag.getMethodNames().add("writeByte");
			parcelBag.getMethodNames().add("writeByteArray");
			parcelBag.getMethodNames().add("writeCharArray");
			parcelBag.getMethodNames().add("writeDouble");
			parcelBag.getMethodNames().add("writeDoubleArray");
			parcelBag.getMethodNames().add("writeFloat");
			parcelBag.getMethodNames().add("writeFloatArray");
			parcelBag.getMethodNames().add("writeInt");
			parcelBag.getMethodNames().add("writeIntArray");
			parcelBag.getMethodNames().add("writeLong");
			parcelBag.getMethodNames().add("writeLongArray");

		}
		if (captureParcelBigIO) {
			parcelBag.getMethodNames().add("readBundle");
			parcelBag.getMethodNames().add("writeBundle");
			parcelBag.getMethodNames().add("writeSparseBooleanArray");
			parcelBag.getMethodNames().add("readSparseBooleanArray");
			parcelBag.getMethodNames().add("readString");
			parcelBag.getMethodNames().add("readStringArray");
			parcelBag.getMethodNames().add("writeString");
			parcelBag.getMethodNames().add("writeStringArray");
		}

		GenericClassBag broadCastReceiver = new GenericClassBag();
		broadCastReceiver.setName("IPC-Broadcast");
		broadCastReceiver.getClazzes().add(android.content.BroadcastReceiver.class.getName());
		broadCastReceiver.getArguments().add(android.os.Bundle.class.getName());
		broadCastReceiver.getReturns().add(android.os.Bundle.class.getName());
		broadCastReceiver.getMethodNames().add("getResultData");
		broadCastReceiver.getMethodNames().add("getResultCode");
		broadCastReceiver.getMethodNames().add("setResultData");
		broadCastReceiver.getMethodNames().add("setResultCode");

		MultipleClassBag multiBag = new MultipleClassBag("IPC", ipcPendingIntent, parcelBag, intentCreation,
				broadCastReceiver);
		return multiBag;
	}

	public static IClassBag getMgmt() {
		GenericClassBag pkgMgmt = new GenericClassBag();
		pkgMgmt.setName("MGMT");
		pkgMgmt.getClazzes().add(android.content.pm.PackageManager.class.getName());
		pkgMgmt.getClazzes().add(android.content.pm.PackageInstaller.class.getName());
		pkgMgmt.getArguments().add(java.lang.String.class.getName());
		pkgMgmt.getArguments().add(android.content.pm.PermissionInfo.class.getName());
		pkgMgmt.getArguments().add(android.content.pm.PermissionGroupInfo.class.getName());
		pkgMgmt.getArguments().add(android.content.ComponentName.class.getName());
		pkgMgmt.getArguments().add(android.content.pm.ApplicationInfo.class.getName());
		pkgMgmt.getArguments().add(android.content.pm.InstallSourceInfo.class.getName());
		pkgMgmt.getArguments().add(android.content.pm.PackageInstaller.class.getName());
		
		pkgMgmt.getReturns().addAll(pkgMgmt.getArguments());

		pkgMgmt.getMethodNames().add("checkSignatures");
		pkgMgmt.getMethodNames().add("clearInstantAppCookie");
		pkgMgmt.getMethodNames().add("currentToCanonicalPackageNames");
		pkgMgmt.getMethodNames().add("extendVerificationTimeout");
		pkgMgmt.getMethodNames().add("getActivityBanner");
		pkgMgmt.getMethodNames().add("getInstalledModules");
		pkgMgmt.getMethodNames().add("getInstalledPackages");
		pkgMgmt.getMethodNames().add("getPackagesHoldingPermissions");
		
		GenericClassBag context = new GenericClassBag();
		context.setName("ctx");
		context.getClazzes().add(android.content.Context.class.getName());
		context.getExcludedMethodNames().add("obtainStyledAttributes");
		context.getExcludedMethodNames().add("getText");
		context.getExcludedMethodNames().add("getString");
		context.getExcludedMethodNames().add("getDrawable");
		context.getExcludedMethodNames().add("getColor");
		context.setAllClassMethods(true);
		
		
		GenericClassBag managers = new GenericClassBag();
		managers.getClazzes().add(android.app.AppOpsManager.class.getName());
		managers.getClazzes().add(android.app.KeyguardManager.class.getName());
		managers.getClazzes().add(android.app.NotificationManager.class.getName());
		managers.getClazzes().add(android.content.pm.ShortcutManager.class.getName());
		managers.getClazzes().add(android.location.LocationManager.class.getName());
		managers.getClazzes().add(android.net.ConnectivityManager.class.getName());
		managers.getClazzes().add(android.net.wifi.WifiManager.class.getName());
		managers.getClazzes().add(android.os.UserManager.class.getName());
		managers.getClazzes().add(android.view.autofill.AutofillManager.class.getName());
		managers.getClazzes().add(android.telephony.TelephonyManager.class.getName());
		managers.getClazzes().add(android.content.pm.PackageManager.class.getName());
		managers.getClazzes().add(android.telephony.SmsManager.class.getName());
		managers.getClazzes().add(android.telephony.gsm.GsmCellLocation.class.getName());
		managers.getClazzes().add(android.net.wifi.WifiInfo.class.getName());
		managers.getClazzes().add(android.accounts.AccountManager.class.getName());
		managers.getClazzes().add(android.accounts.AccountManager.class.getName());
		managers.getClazzes().add(android.net.wifi.p2p.WifiP2pManager.class.getName());
		managers.getClazzes().add(android.net.nsd.NsdManager.class.getName());
		managers.getClazzes().add(android.app.KeyguardManager.class.getName());
		managers.getClazzes().add(android.content.ClipboardManager.class.getName());
		managers.getClazzes().add(android.drm.DrmManagerClient.class.getName());
		managers.getClazzes().add(android.app.SearchManager.class.getName());
		managers.getClazzes().add(android.os.BatteryManager.class.getName());
		managers.getClazzes().add(android.os.HardwarePropertiesManager.class.getName());
		managers.getClazzes().add(android.os.VibratorManager.class.getName());
		managers.getClazzes().add(android.os.Build.class.getName());
		managers.setAllClassMethods(true);
		
		GenericClassBag managers2 = new GenericClassBag();
		managers2.getClazzes().add(android.view.accessibility.AccessibilityManager.class.getName());
		managers2.getExcludedMethodNames().add("isEnabled");
		managers2.setAllClassMethods(true);

		/*
		 * mgmt.getMethodNames().add("getopenFileInput");
		 * mgmt.getMethodNames().add("openOrCreateDatabase");
		 * mgmt.getMethodNames().add("startActivities");
		 * mgmt.getMethodNames().add("startActivity");
		 * mgmt.getMethodNames().add("startForegroundService");
		 * mgmt.getMethodNames().add("startIntentSender");
		 * mgmt.getMethodNames().add("startService");
		 * mgmt.getMethodNames().add("stopService");
		 * mgmt.getMethodNames().add("unbindService");
		 * mgmt.getMethodNames().add("bindService");
		 * mgmt.getMethodNames().add("unregisterReceiver");
		 * mgmt.getMethodNames().add("registerReceiver");
		 * mgmt.getMethodNames().add("updateServiceGroup");
		 */
		MultipleClassBag res = new MultipleClassBag("Management", pkgMgmt, context, managers, managers2);
		return res;
	}
	
	public static IClassBag networkPoints() {
		GenericClassBag url = new GenericClassBag();
		url.setName("Network1");
		url.getClazzes().add(java.net.URL.class.getName());
		url.setAllClassMethods(true);
		
		GenericClassBag urlConnection = new GenericClassBag();
		urlConnection.setName("Network");
		urlConnection.getClazzes().add(java.net.HttpURLConnection.class.getName());
		urlConnection.getExcludedMethodNames().add("getFollowRedirects");
		urlConnection.setAllClassMethods(true);
		
		
		GenericClassBag ssl = new GenericClassBag();
		ssl.setName("Network-ssl");
		ssl.getClazzes().add(javax.net.ssl.SSLContext.class.getName());
		ssl.getClazzes().add(java.net.Socket.class.getName());
		ssl.getClazzes().add(javax.net.ssl.SSLSocketFactory.class.getName());
		ssl.setAllClassMethods(true);
		ssl.getExcludedMethodNames().add("isConnected");
		ssl.getExcludedMethodNames().add("isClosed");
		
		GenericClassBag okHttp = new GenericClassBag();
		okHttp.getClazzes().add(okhttp3.OkHttpClient.class.getName());
		okHttp.getClazzes().add(okhttp3.Request.class.getName());
		okHttp.getClazzes().add(okhttp3.Response.class.getName());
		okHttp.getExcludedMethodNames().add("newBuilder");
		okHttp.setAllClassMethods(true);
		
		GenericClassBag retrofit2Bag = new GenericClassBag();
		retrofit2Bag.getClazzes().add(retrofit2.Call.class.getName());
		retrofit2Bag.getClazzes().add(retrofit2.Callback.class.getName());
		retrofit2Bag.getClazzes().add(retrofit2.Response.class.getName());
		retrofit2Bag.setAllClassMethods(true);
		
		MultipleClassBag res = new MultipleClassBag("Network", url, urlConnection, ssl, okHttp, retrofit2Bag);
		return res;
	}
	
	public static IClassBag cryptoAPIs() {
		GenericClassBag keyManager = new GenericClassBag();
		keyManager.getClazzes().add(javax.net.ssl.KeyManagerFactory.class.getName());
		keyManager.getClazzes().add(javax.net.ssl.KeyManager.class.getName());
		keyManager.getClazzes().add(javax.net.ssl.TrustManager.class.getName());
		keyManager.getClazzes().add(javax.net.ssl.TrustManager.class.getName());
		keyManager.getClazzes().add(android.security.keystore.KeyGenParameterSpec.class.getName());
		keyManager.getClazzes().add(android.security.keystore.KeyProperties.class.getName());
		keyManager.getClazzes().add(android.security.keystore.KeyProtection.class.getName());
		keyManager.getClazzes().add(android.security.keystore.KeyInfo.class.getName());
		keyManager.getClazzes().add(java.security.KeyPair.class.getName());
		keyManager.getClazzes().add(java.security.KeyPairGenerator.class.getName());
		keyManager.getClazzes().add(java.security.KeyStore.class.getName());
		keyManager.getClazzes().add(java.security.PrivateKey.class.getName());
		keyManager.getClazzes().add(java.security.PublicKey.class.getName());
		keyManager.getClazzes().add(java.security.Signature.class.getName());
		keyManager.getClazzes().add(java.security.PrivateKey.class.getName());
		keyManager.getClazzes().add(javax.crypto.Cipher.class.getName());
		keyManager.getClazzes().add(javax.crypto.KeyGenerator.class.getName());
		keyManager.setAllClassMethods(true);
		return keyManager;
		
	}

	public static List<IClassBag> getApis() {
		List<IClassBag> apiBag = new LinkedList<IClassBag>();
		apiBag.add(buildGeoApi());
		apiBag.add(buildFileApi());
		apiBag.add(buildSqliteDatabaseApiBag());
		apiBag.add(buildHardwareBag());
		apiBag.add(buildIPCIntents());
		apiBag.add(getMgmt());
		apiBag.add(networkPoints());
		apiBag.add(cryptoAPIs());
		return apiBag;
	}

}
