# Cargar el entorno virtual en ENVS/Dask

## Uso:
1. git clone del repo.
2. Descargar de horizon el fichero de credenciales de un tenant con cuota suficiente para lo que se desea construir
(Compute -> Access & Security -> API Access)
    1. Añadir la variable con la CA de TID export OS_CACERT=...

2. Copiar el ejemplo de fichero de entorno (environment_sample.yaml) a otro nombre (ej cap-environment.yaml) y editar los valores al gusto

~~~
 openstack stack create -e EPG-env.yaml -t heat-hadoop-cluster.yaml dask-cluster --wait -v
 openstack server list | awk '{print $9}' | grep 10.95 > clientList.txt 

penstack stack delete dask-cluster -y  -v --wait

~~~

