#!/bin/bash

echo "Enter IP address:"
read ip

echo "Enter port number:"
read port

nping -c 1 -p $port $ip --tcp
