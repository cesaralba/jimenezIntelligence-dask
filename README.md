# Cargar el entorno virtual en ENVS/Dask

## Uso:
1. git clone del repo.
2. Descargar de horizon el fichero de credenciales de un tenant con cuota suficiente para lo que se desea construir
(Compute -> Access & Security -> API Access)
    1. Añadir la variable con la CA de TID export OS_CACERT=...

2. Copiar el ejemplo de fichero de entorno (environment_sample.yaml) a otro nombre (ej cap-environment.yaml) y editar los valores al gusto

#Crear
~~~
 openstack stack create -e EPG-env.yaml -t heat-dask-cluster.yaml dask-cluster --wait
 mkdir -p /tmp/dask
 python heat-inventory.py -s dask-cluster -d /tmp/dask
~~~

#Destruir
~~~


openstack stack delete dask-cluster -y  --wait

~~~

#Lanzar cosas
~~~
. ~/Dropbox/ENVS/Dask/loadEnv

dask-scheduler

dask-ssh  --ssh-username cloud-user --remote-python /bin/python --worker-port 8787 --nanny-port 8788 --nohost  --hostfile clientList.txt

~~~

/var/lib/cloud/instance/scripts/part-001
