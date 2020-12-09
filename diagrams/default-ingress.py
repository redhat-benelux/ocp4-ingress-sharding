from diagrams import Cluster, Diagram
from diagrams.gcp.network import Router, LoadBalancing, DNS
from diagrams.k8s.compute import Pod
from diagrams.k8s.network import Ingress
from diagrams.generic.blank import Blank

graph_attr = { 
	# "splines": "curved"
}

with Diagram("OCP4 Default Ingress", show=False, direction="LR", graph_attr=graph_attr):
	dns = DNS("*.apps.dta.my.lab")
	lbint = LoadBalancing("HAProxy")

	with Cluster("OpenShift Cluster"):
		routerext = Ingress("default") 

		with Cluster("Workers"):
			with Cluster("Projects"):
				with Cluster("proj-app-01"):
					workersint = [Pod("myApp")]
            
				with Cluster("proj-app-02"):
					workersext = [Pod("myApp")]

	dns >> lbint
	lbint >> routerext
	routerext >> workersint
	routerext >> workersext 


