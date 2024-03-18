import socket
import threading
import time
import pickle
import os

encerrarPrograma = False

class Node:
    def __init__(self, node_id, node_address, k=50):
        self.node_id = node_id
        self.node_address = node_address
        self.k = k
        self.data = {}
        self.lista_nodes = []
        self.multicast_group = '224.1.1.1'
        self.multicast_port = 9876
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.multicast_group) + socket.inet_aton('0.0.0.0'))
        self.discovery_socket.bind(('', self.multicast_port))

        self.private_directory = os.path.join(os.getcwd(), 'private_data')
        if not os.path.exists(self.private_directory):
            os.makedirs(self.private_directory)
		

    def _send_discovery_message(self):
        # Send discovery message to the multicast group
        known_nodes = ",".join([f"{node_id}:{ip}" for node_id, ip in self.lista_nodes])
        while encerrarPrograma == False:
            message = f"DISCOVER|{self.node_id}|{known_nodes}"
            self.discovery_socket.sendto(message.encode(), (self.multicast_group, self.multicast_port))
            time.sleep(2)

    def _listen_for_discovery(self):
        # Listen for discovery messages on the multicast group
        while encerrarPrograma == False:
            data, addr = self.discovery_socket.recvfrom(1024)
            message = data.decode()
            #print(message)
            discovery_node_id = message.split("|")[1]
            discovered_node = PrimitiveNode(discovery_node_id, addr[0])
            if message.startswith("DISCOVER") and message.split("|")[1] != self.node_id and discovered_node not in self.lista_nodes:
               
                #if addr[0] == peer.node_address:
                if addr[0] in [peer.node_address for peer in self.lista_nodes]:
                    continue

                print(f"Nó {discovery_node_id} descoberto no endereço {addr[0]}")
                self.lista_nodes.append(discovered_node)

    def showPeers(self):
        if not self.lista_nodes:
            print('Nenhum Peer Conectado a Rede')
            return
        
        i = 1
        for peer in self.lista_nodes:
            print(f'Peer {i}\n ID: {peer.node_id}\n Address: {peer.node_address}')
            print()
            i += 1

    def readFile(self, filename):
        try:
            with open(os.path.join(self.private_directory, f'{filename}.txt'), 'r+') as file:
                text_lines = file.readlines()
        except:
            print('File not found')
            return False
    
        return text_lines

    def sendFile(self, filename, address):
        try:
            text_lines = self.readFile(filename)
        except:
            print('Error')
            return
    
        control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        control_message = ('Sending File', 'FILE')
        b_control = pickle.dumps(control_message)
        control_socket.sendto(b_control, (address, 55556))

        time.sleep(5)

        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.connect((address, 55555))
   
        blob = (filename, 'FILE')
        buffered_blob = pickle.dumps(blob)
        file_socket.send(buffered_blob)

        if not text_lines:
            return
   
        for line in text_lines:
            blob = (line, 'FILE')
            buffered_blob = pickle.dumps(blob)
            file_socket.send(buffered_blob)
            time.sleep(0.1)

        blob = ('COMPLETE', 'FILE')
        buffered_blob = pickle.dumps(blob)
        file_socket.send(buffered_blob)

        file_socket.close()
        control_socket.close()

    def receiveFile(self):
        server_address = '0.0.0.0'
        server_port = 55555

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((server_address, server_port))

        server.listen(5)

        client_socket, client_address = server.accept()
    
        text = list()

        while True:
            data = client_socket.recv(1024)

            if not data:
                break

            debuffered_data = pickle.loads(data)
            message_text = debuffered_data[0]

            if message_text == 'COMPLETE':
                break
            text.append(message_text)

        server.close()
        return text

    def buildFile(self, text_list):
        filename = text_list[0]
        with open(os.path.join(self.private_directory, f'{filename}.txt'), 'w+') as file:
            for line in text_list[1:]:
                print(line)
                file.write(line)

    def requestFile(self, filename, address):

        request_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        blob = (filename, 'REQUEST')
        buffered_blob = pickle.dumps(blob)

        request_socket.sendto(buffered_blob, (address, 55556))

        time.sleep(3)

        request_socket.close()

 
    def receive_messages(self):
        # Configurar o socket UDP para receber mensagens
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(('0.0.0.0', 55556))

        while encerrarPrograma == False:
            # Receber dados do cliente
            data, addr = server.recvfrom(1024)
            
            extensive_data = pickle.loads(data)

            message = extensive_data[0]
            code = extensive_data[1]

            print(f"Received message from {addr}: {message}")

            ip_address = addr[0]

            if code == 'FILE':
                file = self.receiveFile()
                print(file)   
                self.buildFile(file)

            if code == 'REQUEST':
                try:
                    print('entrou')
                    file = self.readFile(message)
                    if file == False:
                        print('Não tenho')
                    else:
                        self.sendFile(message, address=ip_address)
                except Exception as e:
                    print(f'{self.node_id}: Nao tenho')
                    continue


            if code == 'DISCONNECTING':
                for peer in self.lista_nodes:
                    if peer.node_address == ip_address:
                        self.lista_nodes.remove(peer)

    def send_message(self, dest_id, message, code):
        dest_ip = None

        dest_port = 55556  # Corrected port number

        for peer in self.lista_nodes:
            if dest_id == peer.node_id:
                dest_ip = peer.node_address

        # Configurar o socket UDP para enviar mensagens
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        blob = (message, code)
        buffered_blob = pickle.dumps(blob)

        # Enviar mensagem para o destino
        if dest_ip is not None:
            # Enviar mensagem para o destino
            client.sendto(buffered_blob, (dest_ip, dest_port))
        else:
            print(f"Peer de destino nao encontrado")

    def exitNetwork(self):
        if not self.lista_nodes:
            return
        
        for peer in self.lista_nodes:
            self.send_message(peer.node_id, '', 'DISCONNECTING')

class PrimitiveNode:
    def __init__(self, node_id, node_address):
        self.node_id = node_id
        self.node_address = node_address

if __name__ == "__main__":
    id = str(input("Digite um ID: "))
    address = socket.gethostbyname(socket.gethostname())
    new_node = Node(id, address)
    
    broadcasting_thread = threading.Thread(target=new_node._send_discovery_message)
    broadcasting_thread.start()

    discovery_thread = threading.Thread(target=new_node._listen_for_discovery)
    discovery_thread.start()
    
    receiver_thread = threading.Thread(target=new_node.receive_messages)
    receiver_thread.start() 

    while True:
        print('----- MENU -----')
        print('1 - Enviar Mensagem')
        print('2 - Enviar Arquivo')
        print('3 - Mostrar Peers')
        print('4 - Pedir Arquivo')
        print('5 - Sair da Rede')

        option = input('Digite uma opcao: ')
        print()

        if option == '1':
            id_send = input('Digite o id do recebedor: ')
            message = input('Digite a mensagem: ')
            print()

            new_node.send_message(id_send, message, 'MESSAGE')
            continue 

        if option == '2':
            send_id = input('Digite o id: ')
            nome_arquivo = input('Digite o nome do arquivo: ')

            for peer in new_node.lista_nodes:
                if send_id == peer.node_id:
                    new_node.sendFile(nome_arquivo, peer.node_address)
                    
            continue

        if option == '3':
            new_node.showPeers()
            continue


        if option == '4':
            filename = input('Digite o nome do arquivo: ')
            try:
                with open(os.path.join('private_data', f'{filename}.txt'), 'r+') as file:
                    text_lines = file.readlines()
                print('você já tem o arquivo')
            except:
                print('entrou aqui')
                for peer in new_node.lista_nodes:
                    new_node.requestFile(filename, peer.node_address)

        if option == '5':
            discovery_thread.join()
            receiver_thread.join()
            broadcasting_thread.join()
            new_node.exitNetwork()
            encerrarPrograma = True
            break