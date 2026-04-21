import React from "react";

import { Icon } from "@chakra-ui/react";
import {
  MdCloudUpload,
  MdApps,
  MdShield,
} from "react-icons/md";

// Views
import Upload from "views/admin/upload";
import AppsList from "views/admin/apps";
import VirusTotalHub from "views/admin/virustotal";

const routes = [
  {
    name: "Upload APK",
    layout: "/admin",
    path: "/upload",
    icon: <Icon as={MdCloudUpload} width='20px' height='20px' color='inherit' />,
    component: Upload,
  },
  {
    name: "Apps",
    layout: "/admin",
    path: "/apps",
    icon: <Icon as={MdApps} width='20px' height='20px' color='inherit' />,
    component: AppsList,
  },
  {
    name: "VirusTotal",
    layout: "/admin",
    path: "/virustotal",
    icon: <Icon as={MdShield} width='20px' height='20px' color='inherit' />,
    component: VirusTotalHub,
  },
];

export default routes;
