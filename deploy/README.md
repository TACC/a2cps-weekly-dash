# covid19 dash deploy on kubernetes

## status

To see running status, `kubectl get all`. Should look something like this:

    # kubectl get all 
    NAME                           READY   STATUS    RESTARTS   AGE
    pod/covid19-7f9bf5f4dd-bnx48   1/1     Running   0          13m
    pod/covid19-7f9bf5f4dd-dr2pp   1/1     Running   0          13m
    pod/covid19-7f9bf5f4dd-qdnpr   1/1     Running   0          13m
    
    NAME              TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
    service/covid19   NodePort   10.99.173.10     <none>        8050:30851/TCP   13m
    
    NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/covid19   3/3     3            3           14m
    
    NAME                                 DESIRED   CURRENT   READY   AGE
    replicaset.apps/covid19-7f9bf5f4dd   3         3         3       14m


## start 

    ./burnup

Does not hurt anything to run more than once, if you change deploy.yml just run it again.

## stop

    ./burndown 

(then follow the instructions). Should not really need to do this very often.

## restart with new docker image

If you push a new image to docker hub, run 

    ./pullnewimage


## logs

To grab logs from one pod (should be similar to the others:

    kubectl logs deploy/covid19

To see all logs, you can try this, which grabs logs from each running pod:

    ./podlogs 



