import React from "react";

import { Icon } from "@chakra-ui/react";
import {
  MdBarChart,
  MdPerson,
  MdHome,
  MdLock,
  MdOutlineShoppingCart,
} from "react-icons/md";

// Admin Imports
import MainDashboard from "views/admin/default";
import Graph from "views/admin/graph";

const routes = [
  {
    name: "Project",
    layout: "/admin",
    path: "/default",
    icon: <Icon as={MdHome} width='20px' height='20px' color='inherit' />,
    component: MainDashboard,
  },
  {
    name: "Graph",
    layout: "/admin",
    path: "/graph",
    icon: <Icon as={MdHome} width='20px' height='20px' color='inherit' />,
    component: Graph,
  },
];

export default routes;
