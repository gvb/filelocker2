# -*- coding: utf-8 -*-

class ClusterNode:
    #CREATE TABLE `cluster_node` (
    #`cluster_node_id` MEDIUMINT NOT NULL DEFAULT 0,
    #`cluster_node_unique_url` TEXT NOT NULL,
    #`cluster_node_is_master` TINYINT(1) DEFAULT 1,
    #`cluster_node_last_check_in` DATETIME DEFAULT NULL,
    #PRIMARY KEY (`cluster_node_id`) )
    def __init__ (self, nodeId, nodeURL, isMaster, lastCheckIn ):
        self.clusterNodeId = nodeId
        self.clusterNodeURL = nodeURL
        self.clusterNodeIsMaster = isMaster
        self.clusterNodeLastCheckIn = lastCheckIn
        