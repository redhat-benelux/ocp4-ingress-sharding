## OpenShift Container Platform 4 Traffic Management
This repo is providing a generic overview of OCP4 traffic management from an ingress controller perspective. One option is route sharding or the ability to have multiple dedicated ingress controllers to handle the incoming traffic with a dedicated/custom route to a specific workload while using the selector capabilities at route or namespace level to elect automatically which ingress controller will be used to create the route. 

Table of Contents
- [OpenShift Container Platform 4 Traffic Management](#openshift-container-platform-4-traffic-management)
  * [Scenario overview](#scenario-overview)
    * [Default behavior of OCP4 ingress controller](#default-behavior-of-ocp4-ingress-controller)
    * [Adding a new ingress controller for sharding the traffic](#adding-a-new-ingress-controller-for-sharding-the-traffic)
      - [Setup Requirements](#setup-requirements)
      - [Additional Ingress Controller](#additional-ingress-controller)
      - [Testing the new path](#testing-the-new-path)
      - [Using a routeSelector](#using-a-routeselector)
      - [Using a namespaceSelector](#using-a-namespaceselector)

## Scenario overview 

Considering the following as one of the many potential scenario; using one OCP4 cluster for the DTA (Dev, Test, and Acceptance) activities, it might be of interests to welcome users for UAT (User Acceptance Testing) activities from a less secure network zone (end-users from different department or even from the outside world) than the usual internal organization's network. 

By default, OCP4 deployment will be using a single ingress controller that will handle any incoming traffic and generate the routes based on the default settings (setting inherited from the installation process, later modifications and also from an application deployment perspective if any in place). 

However, from a security standpoint, having the internal and external traffic in such funneling approach might light up the red flag as there is not physical or logical network segmentation or key differentiator to help flag the origin and destination of such traffic which could lead to an increased attack surface on the OCP4 cluster. 

There are different ways to mitigate these concerns with different level of complexity. A good starting point is to leverage the existing component in-place and already in-use aka the ingress-controller operator by creating a new ingress controller that will handle all the external traffic towards the relevant pods  

The current setup is composed of a single OCP4 cluster on which there are "internal only" workloads being served via routes using the domain construct **apps.dta.my.lab**. 

Some workloads running in acceptance will welcome end-users from outside the organization as field test users using routes using the domain construct **apps.uat.my.lab**.

Note: this setup doesn't provide a workload isolation at any physical layers but at a logical one. If a physical isolation is (also) required, this solution is called network node isolation which can also be configured with sharding.

### Default behavior of OCP4 ingress controller
The below figure provides an overview of the default out of the box ingress controller setup with the default routing construct.

This would serve only the requests towards the internal workloads using the **apps.dta.my.lab** route construct.

![](https://raw.githubusercontent.com/rovandep/ocp4-ingress-sharding/master/diagrams/ocp4_default_ingress.png)


From a CLI perspective, here is a recent lab deployment overview of OCP4.5.13 of the default out of the box ingress controller operator sitting within the namespace openshift-ingress-operator.
Note that some specific settings might have different values due to the deployment type like the endpointPublishingStrategy which directly linked to the actual type platform on which OCP is running (hyperscaler, bare metal, ...)
```
oc get ingresscontrollers -n openshift-ingress-operator
NAME      AGE
default   13h

oc get pod -n openshift-ingress
NAME                              READY   STATUS    RESTARTS   AGE
router-default-59c648bd6f-gmhqq   1/1     Running   1          13h
router-default-59c648bd6f-szz77   1/1     Running   1          13h
```

The following command will provide a configuration extract of the default ingress controller: 
```
$ oc get ingresscontroller default -n openshift-ingress-operator -o yaml
apiVersion: operator.openshift.io/v1
kind: IngressController
metadata:
  finalizers:
  - ingresscontroller.operator.openshift.io/finalizer-ingresscontroller
  name: default
  namespace: openshift-ingress-operator
spec:
  replicas: 2
  domain: apps.dta.my.lab
  endpointPublishingStrategy:
    type: HostNetwork
  observedGeneration: 1
  selector: ingresscontroller.operator.openshift.io/deployment-ingresscontroller=default
  tlsProfile:
    ciphers:
    - TLS_AES_128_GCM_SHA256
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
    - ECDHE-ECDSA-AES128-GCM-SHA256
    - ECDHE-RSA-AES128-GCM-SHA256
    - ECDHE-ECDSA-AES256-GCM-SHA384
    - ECDHE-RSA-AES256-GCM-SHA384
    - ECDHE-ECDSA-CHACHA20-POLY1305
    - ECDHE-RSA-CHACHA20-POLY1305
    - DHE-RSA-AES128-GCM-SHA256
    - DHE-RSA-AES256-GCM-SHA384
    minTLSVersion: VersionTLS12
```

### Adding a new ingress controller for sharding the traffic

#### Setup Requirements
To achieve the goal of the [Scenario overview](#scenario-overview), the followings need to be addressed:

- create wildcard DNS record for the new (sub)domain **apps.uat.my.lab** 
- create a load balancer context for the new domain **apps.uat.my.lab**
- create a new ingress controller to handle the routing construct

Point 1 & 2 are out of scope here and are most likely in 99% of the case a repeat of the OCP4 installation settings for DNS and loadbalancer.

### Additional Ingress Controller  
The below figure provides an overview of the final desired configuration state. 

Note the changes between the default ingress controller setup and this; a new ingress controller is created in order to handle all the requests for the **apps.uat.my.lab** domain and route them to the appropriate pod along the existing default one handling all the requests for the **apps.dta.my.lab** domain.

![](https://raw.githubusercontent.com/rovandep/ocp4-ingress-sharding/master/diagrams/ocp4_route_sharding.png)

Here is an example of the new ingress controller for the external traffic:
```
$ cat router-external.yml
apiVersion: v1
items:
- apiVersion: operator.openshift.io/v1
  kind: IngressController
  metadata:
    name: external
    namespace: openshift-ingress-operator
  spec:
    domain: apps-ext.cluster.my.lab
    endpointPublishingStrategy:
      type: HostNetwork
    nodePlacement:
      nodeSelector:
        matchLabels:
          node-role.kubernetes.io/worker: ""
    routeSelector:
      matchLabels:
        type: external
  status: {}
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
```
Note: the above example is linked to the specifics of the lab used for this article. One key elements that needs to be adapted is the endpointPublishingStrategy type (here "HostNetwork") which can be set accordingly to your environment by executing the following command as per the previous chapter:

``` 
oc get ingresscontroller default -n openshift-ingress-operator -o yaml
``` 

To create the new ingress controller:
```
$ oc apply -f router-external.yml 
ingresscontroller.operator.openshift.io/external created
``` 

To verify the results:
```
$ oc get ingresscontroller -n openshift-ingress-operator
NAME       AGE
default    14h
external   70s
``` 

To check the configuration change at the cluster level:
```
$ oc get svc -n openshift-ingress
NAME                       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                   AGE
router-internal-default    ClusterIP   172.30.173.145   <none>        80/TCP,443/TCP,1936/TCP   14h
router-internal-external   ClusterIP   172.30.110.126   <none>        80/TCP,443/TCP,1936/TCP   92s
```

To check the pod deployment of the ingress operators:
```
$ oc get pod -n openshift-ingress
NAME                               READY   STATUS    RESTARTS   AGE
router-default-59c648bd6f-gmhqq    1/1     Running   1          14h
router-default-59c648bd6f-szz77    1/1     Running   1          14h
router-external-74ddf649f8-4d4f4   1/1     Running   0          3m9s
router-external-74ddf649f8-mvq8z   1/1     Running   0          3m8s
```

### Testing the new path
To test the newly created ingress controller, let's create a new project and deploy an basic application:

``` 
oc new-project sharding-test
oc new-app django-psql-example
``` 

Doing so will results in the deployment of the django application with the following route:

```
oc get route -n sharding-test
curl -I -- route --
```

As there isn't any specific labeling, the exposed route is using the router "default" using the **apps.dta.my.lab** endpoint.
From a pure deployment perspective, the route can be part of a configuration map like:

``` 
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: django-psql-example
    template: django-psql-example
    type: external
  name: django-psql-example
  namespace: sharding-test
spec:
  host: django-psql-example-external-project.apps.uat.cluster.my.lab
  subdomain: ""
  to:
    kind: Service
    name: django-psql-example
    weight: 100
  wildcardPolicy: None
```

Deleling the current route and applying the above configuration will provide the necessary route to use the newly created ingress controller.

```
oc delete route django-psql-example -n sharding-test
oc apply -f route-django.yml
curl -I -- route --
```

However, digging a bit further within the route configuration outcome, the default behavior is still there. Indeed, we applied the proper configuration for the route but OCP4 applied the default route configuration too ending up with two routes:

```
oc describe route django-psql-example -n sharding-test 
``` 

### Using a routeSelector
As seen previously, the despite of creating a custom route for our django application, the default behavior still kicked in and created a route with the router "default".

To avoid such situation, there is a modification that can be make at the ingress controller level to specify the usage. The following configuration map can help modifiy the newly create router to include the routeSelector parameter:

``` 
apiVersion: v1
items:
- apiVersion: operator.openshift.io/v1
  kind: IngressController
  metadata:
    name: external
    namespace: openshift-ingress-operator
  spec:
    domain: apps.uat.cluster.my.lab
    endpointPublishingStrategy:
      type: HostNetwork
    nodePlacement:
      nodeSelector:
        matchLabels:
          node-role.kubernetes.io/worker: ""
    routeSelector:
      matchLabels:
        type: external
  status: {}
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
```

To go further on the both, this can be done also for the router "default" so that the overall behavior is matching the expected sharding construct:

```
apiVersion: v1
items:
- apiVersion: operator.openshift.io/v1
  kind: IngressController
  metadata:
    name: default 
    namespace: openshift-ingress-operator
  spec:
    routeSelector:
      matchLabels:
        type: internal
  status: {}
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
``` 

Note: obviously from a configuration standpoint, this should be included from the earliest stage of the external router configuration.

From the above, the configuration introduces by using **oc apply** like previously done the followings:
* internal for dta needs
* external for uat needs 

Note: These changes will directly impact the existing workload like our test application. Checking again the route configuration with **oc describe route** like previously done will show that the internal mechanics removed the route with the router "default".

#### How to use the routeSelector
From the current django application deployed on OCP4 and the route configuration modification done in [Testing the new path](#testing-the-new-path), the overall is working "magically" as this article ramped up the application towards the desired state.

However, deploying a new canned application like the django test will result in a none working route because the configuration doesn't contain the routeSelector. This can be fixed by editing the deployment configuration or at a later stage like we did by adding the routeSelector to match the label "internal" or "external" from this example. 

This approach is mostly ok when the application deployment configuration is handled by the application or devops team and will take this into consideration by adding the appropriate configuration changes. 

### Using a namespaceSelector
Another approach in regards of sharding is to define that the namespace/project will be defining if the service will be exposed with one or the other ingress controller. In a very similar way, the namespaceSelector is an additional configuration to be applied from an ingress controller level like so:

```
apiVersion: v1
items:
- apiVersion: operator.openshift.io/v1
  kind: IngressController
  metadata:
    name: external
    namespace: openshift-ingress-operator
  spec:
    domain: apps.uat.cluster.my.lab
    endpointPublishingStrategy:
      type: HostNetwork
    nodePlacement:
      nodeSelector:
        matchLabels:
          node-role.kubernetes.io/worker: ""
    namespaceSelector:
      matchLabels:
        environment: uat
    routeSelector:
      matchLabels:
        type: external
  status: {}
kind: List
metadata:
  resourceVersion: ""
  selfLink: ""
``` 

The above example shows that when the label "uat" is added on the namespace/project, then all the routes will be created based on the router "external". 

#### How to use the namespaceSelector
Lke for the routeSelector, it's all a question of label. However, for this approach, the label has to be set at the namespace level reducing the need to plan the route configuration at a later stage. 

As a reminder, the following command will add the label to the relevant namespace/project:

``` 
oc label ns sharding-test environment=uat
oc get ns sharding-test -o yaml
``` 

At this stage, the route will be exposed with the appropriate (sub)domain and correct router "external".

