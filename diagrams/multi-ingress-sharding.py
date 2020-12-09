from diagrams import Cluster, Diagram
from diagrams.gcp.network import Router, LoadBalancing, DNS
from diagrams.k8s.compute import Pod
from diagrams.k8s.network import Ingress
from diagrams.generic.blank import Blank

graph_attr = { 
	"splines": "curved"
}

with Diagram("OCP4 Route Sharding ", show=False, direction="LR", graph_attr=graph_attr):
	dnsint = DNS("*.apps.dta.my.lab")
	dnsext = DNS("*.apps.uat.my.lab")
	lbint = LoadBalancing("HAProxy")

	with Cluster("OpenShift Cluster"):
		routerext = Ingress("router-default") 
		routerint = Ingress("router-external")

		with Cluster("Workers"):
			with Cluster("Projects"):
				with Cluster("proj-ext-app-01"):
					workersint = [Pod("myApp")]
            
				with Cluster("proj-int-app-01"):
					workersext = [Pod("myApp")]


	dnsint >> lbint
	dnsext >> lbint 
	lbint >> routerint >> workersint
	lbint >> routerext >> workersext


