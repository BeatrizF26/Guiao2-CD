""" Chord DHT node implementation. """
import socket
import threading
import logging
import pickle
import math
from utils import dht_hash, contains

class FingerTable:
    """Finger Table."""

    def __init__(self, node_id, node_addr, m_bits=10):
        """ Initialize Finger Table."""
        ### --------------------
        self.node_id = node_id
        self.node_addr = node_addr
        self.m_bits = m_bits
        self.table = []                 # Usar uma lista de tuplos em vez do dicionário porque garante que possam haver valores repetidos (se fosse um dicionário não dava para os IDS serem repetidos, como está na notas)

        for i in range(m_bits):
            self.table.append((node_id, node_addr))

    def fill(self, node_id, node_addr):
        """ Fill all entries of finger_table with node_id, node_addr."""

        # Ainda não é preciso pôr o sucessor (é só o ID e o Addr)
        for i in range(0, self.m_bits):
            self.table[i] = (node_id, node_addr)

    def update(self, index, node_id, node_addr):
        """Update index of table with node_id and node_addr."""

        # Atualiza os valores dessa "linha" da tabela (Subtrair um para acertar os valores)
        self.table[index-1] = (node_id, node_addr)

    def find(self, identification):
        """ Get node address of closest preceding node (in finger table) of identification. """

        # Percorrer a tabela de baixo para cima (como está no artigo)
        # E termina no -1 porque é exclusivo (assim garante-se que a primeira linha também é incluída)

        # tive de fazer m_bits-1 pois estava a dar IndexOutOfBounds logo na primeira iteração: index 10 quando só há do 0 ao 9 (por default)

        for i in range(self.m_bits-1, -1, -1):
            node_id, node_addr = self.table[i]

            # Se a identification estiver contido entre os nós
            # Então devolve-se o endereço desse nó que está na fingertable
            if contains(node_id, self.node_id, identification):
                return node_addr

        return self.table[0][1]


    def refresh(self):
        """ Retrieve finger table entries requiring refresh."""

        # Dá return a uma lista de tuplos, onde cada tuplo tem o índice na tabela, o id e o addr
        refreshed = []

        for i in range(self.m_bits):
            index_table = i + 1         # Adicionar um para acertar os indíces
            ID_fingertable = (self.node_id + pow(2, i)) % pow(2, self.m_bits)
            addr_fingertable = self.table[i][1];

            refreshed.append((index_table, ID_fingertable, addr_fingertable))

        return refreshed


    def getIdxFromId(self, id):
        for idx in range(self.m_bits):
            ID_fingerTable = (self.node_id + pow(2, idx))

            # Se o ID calculador for maior do que o maior nó do chord, ele dá a volta
            if (ID_fingerTable > pow(2, self.m_bits) - 1):
                ID_fingerTable = ID_fingerTable - pow(2, self.m_bits)

            # Só se consegue obter o idx quando o ID calculado e o ID passado como argumentos forem iguais
            if ID_fingerTable == id:
                return idx + 1

        return None

    def __repr__(self):
        # Devolve os dados numa string no formato que queremos
        return "\n----FingerTable for NodeID: {}----\n".format(self.node_id) + str(self.as_list)

    @property
    def as_list(self):
        """return the finger table as a list of tuples: (identifier, (host, port)).
        NOTE: list index 0 corresponds to finger_table index 1
        """

        return self.table

class DHTNode(threading.Thread):
    """ DHT Node Agent. """

    def __init__(self, address, dht_address=None, timeout=3):
        """Constructor

        Parameters:
            address: self's address
            dht_address: address of a node in the DHT
            timeout: impacts how often stabilize algorithm is carried out
        """
        threading.Thread.__init__(self)
        self.done = False
        self.identification = dht_hash(address.__str__())
        self.addr = address  # My address
        self.dht_address = dht_address  # Address of the initial Node
        if dht_address is None:
            self.inside_dht = True
            # I'm my own successor
            self.successor_id = self.identification
            self.successor_addr = address
            self.predecessor_id = None
            self.predecessor_addr = None
        else:
            self.inside_dht = False
            self.successor_id = None
            self.successor_addr = None
            self.predecessor_id = None
            self.predecessor_addr = None

        ###
        # self.finger_table = None    #TODO create finger_table
        self.finger_table = FingerTable(self.identification, self.addr)

        self.keystore = {}  # Where all data is stored
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
        self.logger = logging.getLogger("Node {}".format(self.identification))

    def send(self, address, msg):
        """ Send msg to address. """
        payload = pickle.dumps(msg)
        self.socket.sendto(payload, address)

    def recv(self):
        """ Retrieve msg payload and from address."""
        try:
            payload, addr = self.socket.recvfrom(1024)
        except socket.timeout:
            return None, None

        if len(payload) == 0:
            return None, addr
        return payload, addr

    def node_join(self, args):
        """Process JOIN_REQ message.

        Parameters:
            args (dict): addr and id of the node trying to join
        """

        self.logger.debug("Node join: %s", args)
        addr = args["addr"]
        identification = args["id"]

        if self.identification == self.successor_id:  # I'm the only node in the DHT
            self.successor_id = identification
            self.successor_addr = addr

            #TODO update finger table
            self.finger_table.update(1, identification, addr)

            args = {"successor_id": self.identification, "successor_addr": self.addr}
            self.send(addr, {"method": "JOIN_REP", "args": args})
        elif contains(self.identification, self.successor_id, identification):
            args = {
                "successor_id": self.successor_id,
                "successor_addr": self.successor_addr,
            }
            self.successor_id = identification
            self.successor_addr = addr

            #TODO update finger table
            self.finger_table.update(1, identification, addr)
            self.send(addr, {"method": "JOIN_REP", "args": args})

        else:
            #Se não conseguir encontrar nada, então manda para o nó mais pŕoximo
            self.logger.debug("Fing Succesor(%d)", args["id"])
            self.send(self.successor_addr, {"method": "JOIN_REQ", "args": args})

        self.logger.info(self)

    def get_successor(self, args):
        """Process SUCCESSOR message.

        Parameters:
            args (dict): addr and id of the node asking
        """

        #TODO Implement processing of SUCCESSOR message
        ### --------------------
        if contains(self.predecessor_id, self.identification, args["id"]):
            self.send(args["from"], {"method": "SUCCESSOR_REP", "args": {"req_id": args["id"], "successor_id": self.identification, "successor_addr": self.addr}})

        else:
            self.send(self.successor_addr, {"method": "SUCCESSOR", "args": {"id": args["id"], "from": args["from"]}})
        ### --------------------


    def notify(self, args):
        """Process NOTIFY message.
            Updates predecessor pointers.

        Parameters:
            args (dict): id and addr of the predecessor node
        """

        self.logger.debug("Notify: %s", args)
        if self.predecessor_id is None or contains(
            self.predecessor_id, self.identification, args["predecessor_id"]
        ):
            self.predecessor_id = args["predecessor_id"]
            self.predecessor_addr = args["predecessor_addr"]
        self.logger.info(self)

    def stabilize(self, from_id, addr):
        """Process STABILIZE protocol.
            Updates all successor pointers.

        Parameters:
            from_id: id of the predecessor of node with address addr
            addr: address of the node sending stabilize message
        """

        self.logger.debug("Stabilize: %s %s", from_id, addr)
        if from_id is not None and contains(
            self.identification, self.successor_id, from_id
        ):
            # Update our successor
            self.successor_id = from_id
            self.successor_addr = addr
            #TODO update finger table
            # for i in range(len(self.finger_table)):
            #     if self.finger_table[i][0] == from_id:
            #         self.finger_table.update(i, from_id, addr)

            self.finger_table.update(1, self.successor_id, self.successor_addr)


        # notify successor of our existence, so it can update its predecessor record
        args = {"predecessor_id": self.identification, "predecessor_addr": self.addr}
        self.send(self.successor_addr, {"method": "NOTIFY", "args": args})

        # TODO refresh finger_table
        refreshed = self.finger_table.refresh();
        for item in refreshed:
            self.send(item[2], {"method": "SUCCESSOR", 'args': {"id": item[1], "from": self.addr}})

    def put(self, key, value, address):
        """Store value in DHT.

        Parameters:
        key: key of the data
        value: data to be stored
        address: address where to send ack/nack
        """
        key_hash = dht_hash(key)
        self.logger.debug("Put: %s %s", key, key_hash)

        #TODO Replace next code:

        #If key_hash is between the nodes, then the key_hash is responsible to store the informations
        if contains(self.predecessor_id, self.identification, key_hash):
            if key in self.keystore:
                self.send(address, {"method" : "NACK"})
            else:
                self.keystore[key] = value
                self.send(address, {"method" : "ACK"})

        #If not, then it's necessary to check the next nodes until finding the one who's responsible to store the informations
        else:
            self.send(self.finger_table.find(key_hash), {"method": "PUT", "args": {"key": key, "value": value,"from": address}})


    def get(self, key, address):
        """Retrieve value from DHT.

        Parameters:
        key: key of the data
        address: address where to send ack/nack
        """
        key_hash = dht_hash(key)
        self.logger.debug("Get: %s %s", key, key_hash)

        #TODO Replace next code:
        #Check if key_hash is between the nodes
        if contains(self.predecessor_id, self.identification, key_hash):
            #Check if the key is in keystore and get its value
            if key in self.keystore:
                value = self.keystore.get(key)
                self.send(address, {'method': 'ACK', "args": value})

            #If the key isn't in keystore, then it's send a message saying that
            else:
                self.send(address, {"method": "NACK"})

        #If key_hash isn't between the nodes, then it's necessary to check the next nodes until finding the one who's responsible to get the value
        else:
            addr = self.finger_table.find(key_hash)
            self.send(addr, {"method" : "GET", "args" : {"key" : key, "from" : address}})

    def run(self):
        self.socket.bind(self.addr)

        # Loop untiln joining the DHT
        while not self.inside_dht:
            join_msg = {
                "method": "JOIN_REQ",
                "args": {"addr": self.addr, "id": self.identification},
            }
            self.send(self.dht_address, join_msg)
            payload, addr = self.recv()
            if payload is not None:
                output = pickle.loads(payload)
                self.logger.debug("O: %s", output)
                if output["method"] == "JOIN_REP":
                    args = output["args"]
                    self.successor_id = args["successor_id"]
                    self.successor_addr = args["successor_addr"]
                    #TODO fill finger table
                    self.predecessor_id = args["successor_id"]
                    self.predecessor_addr = args["successor_addr"]

                    self.inside_dht = True

                    self.finger_table.fill(self.successor_id, self.successor_addr)
                    self.send(self.successor_addr, {"method" : "NOTIFY", "args" : {'predecessor_id': self.identification, 'predecessor_addr': self.addr}})
                    self.logger.info(self)

        while not self.done:
            payload, addr = self.recv()
            if payload is not None:
                output = pickle.loads(payload)
                self.logger.info("O: %s", output)
                if output["method"] == "JOIN_REQ":
                    self.node_join(output["args"])
                elif output["method"] == "NOTIFY":
                    self.notify(output["args"])
                elif output["method"] == "PUT":
                    self.put(
                        output["args"]["key"],
                        output["args"]["value"],
                        output["args"].get("from", addr),
                    )
                elif output["method"] == "GET":
                    self.get(output["args"]["key"], output["args"].get("from", addr))
                elif output["method"] == "PREDECESSOR":
                    # Reply with predecessor id
                    self.send(
                        addr, {"method": "STABILIZE", "args": self.predecessor_id}
                    )
                elif output["method"] == "SUCCESSOR":
                    # Reply with successor of id
                    self.get_successor(output["args"])
                elif output["method"] == "STABILIZE":
                    # Initiate stabilize protocol
                    self.stabilize(output["args"], addr)
                elif output["method"] == "SUCCESSOR_REP":
                    #TODO Implement processing of SUCCESSOR_REP

                    args = output["args"]
                    req_id = args["req_id"]
                    succ_id = args["successor_id"]
                    succ_addr = args["successor_addr"]

                    idx = self.finger_table.getIdxFromId(req_id)
                    self.finger_table.update(idx, succ_id, succ_addr)
                    
            else:  # timeout occurred, lets run the stabilize algorithm
                # Ask successor for predecessor, to start the stabilize process
                self.send(self.successor_addr, {"method": "PREDECESSOR"})

    def __str__(self):
        return "Node ID: {}; DHT: {}; Successor: {}; Predecessor: {}; FingerTable: {}".format(
            self.identification,
            self.inside_dht,
            self.successor_id,
            self.predecessor_id,
            self.finger_table,
        )

    def __repr__(self):
        return self.__str__()
