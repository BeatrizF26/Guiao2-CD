# Métodos Put e Get (Forma Linear)

### ***Nota:*** Exemplo dado na aula

m = 6 bits -> Número de espaço reservado para o tamanho dos ids (Neste caso vão ser entre 0 e 63, que é 2^m - 1).

Cliente contacta o nó 20 e faz um put (K20, value), como o nó 20 está no chord não há problemas.

- Se for K21, então passa para o próximo nó porque já não está no chord (Vai para o 22).
	
- Se for K51, então vai passar por todos os nós até chegar a um nó que consiga guardar o K51 (pouco eficiente).

# Funcionamento da Finger Table

## Fingertable do nó 20

FingerTable do Nó 20 -> Estrutura que tem o número de entradas (numeradas a partir do 1) igual ao número de bits.

- Para cada linha da Finger Table calcula-se o succID:
    - **succID(n+2^(i-1) % 2^n)**
	- Divide sucessivamente o círculo em partes mais pequenas (Primeiro 20 + 32, depois 20 + 16), o intervalo vai diminuindo à medida que o ID Virtual aumenta.
		
| ID Virtual  |     ID      |     Addr      |  succID(n+2^(i-1) % 2^n)         |
| :---:       |    :----:   |    :----:     |           :---:                  |
| 1           |     22      |   addr(N22)   |  succID(20 + 2^(1-1) % 64) = 22  |
| 2           |     22      |   addr(N22)   |  succID(20 + 2^(2-1) % 64) = 22  |
| 3           |     42      |   addr(N42)   |  succID(20 + 2^(3-1) % 64) = 42  |
| 4           |     42      |   addr(N42)   |  succID(20 + 2^(4-1) % 64) = 42  |
| 5           |     42      |   addr(N42)   |  succID(20 + 2^(5-1) % 64) = 42  |
| 6           |     55      |   addr(N55)   |  succID(20 + 2^(6-1) % 64) = 55  |

Agora se der um put ao K51 no nó 20, usa-se o procedimento Closest-Preciding-Node

- Vai saber que tem de ir para o 42 por causa desse procedimento
- O 42 agora vai ver na sua finger table qual é que deve ser o nó que guarda o value	   

- #### ***Nota:*** Na classe FingerTable, o procedimento corresponde ao método find()

## Fingertable do nó 42

| ID Virtual  |     ID      |     Addr      |  succID(n+2^(i-1))      |
| :---:       |    :----:   |    :----:     |           :---:         |
| 1           |     50      |   addr(N50)   |  succID(42 + 1) = 43	  |
| 2           |     50      |   addr(N50)   |  succID(42 + 2) = 44	  |
| 3           |     50      |   addr(N50)   |  succID(42 + 4) = 46	  |
| 4           |     50      |   addr(N50)   |  succID(42 + 8) = 50	  |
| 5           |     3       |   addr(N3)    |  succID(42 + 16) = 3	  |
| 6           |     10      |   addr(N10)   |  succID(42 + 32) = 10	  |

- #### ***Nota:*** No ID Virtual = 5, o succID = 3 porque o último nó do chord é 57 e daria um resultado maior que isso, o que leva a ter de dar a "volta" ao chord.

## Atualização das Fingertables

Para as finger tables estarem sempre atualizadas dinamicamente, usa-se a função **fix.finger()** que é chamada periodicamente.

- Envia as mensagens do sucessor, não espera pela resposta
- **finger_table[next] = find_successor((n + 2^(next-1) % 2))**
  - Faz só um nó de cada vez, mas pode fazer mais se quisermos

- #### ***Nota:*** No nosso código é a função stabilize() porque já é chamada periodicamente (pode-se incluir uma dentro da outra)

## Métodos a utilizar (Pseudo-Código)

### n.find_successor(id)

    if id in ]n, successor]
		return successor
	else
		n' = closest.proceding_node(id)
	
	return n'.find_successor(id)

---
### n.closest_preceding_node(id)

    for i = m downto 1				
		if finger[i] in (n, id)			
			return finger[i]		
	return n


- Primeiro cria um intervalo entre o ]20, 51] e verifica se o 55 pertence a esse intervalo (Não pertence, então vê o 42)
- Vê os número que estão na finger table e vê se encaixa no intervalo
- Envia uma mensagem successor e, mais tarde, o menu vai receber uma successor reply.
  
---
### def getIdxFromNodeID(id)

    Função dá o ID e recebe o IDX
    Para o nó 20, só pode ser chamada com IDs:
        -> 21, 22, 24, 28, 36, 5

    Retorna, respetivamente, idxs:
        -> 1, 2, 3, 4, 5, 6

- É a função inversa de **f(idx) = (n + 2^(idx-1)) % 2^m**

- #### ***Nota:*** Ter cuidado porque o resto da divisão inteira não seja divisível nas funções inversas

- Em vez de fazer a função inversa, é mais fácil criar um dicionário no construtor da fingertable, porque já se sabe o m e o n
  
---
### def refresh()					
								
	Para o Nó 20:
    [(1, 21, finger_addr[1]),
	(2, 22, finger_addr[2]),
    (3, 24, finger_addr[3))]

- Retorna uma lista de tuplos **[(idx, (n+2^(idx-1) % 2^m), finger_addr[idx])]**

### def fill()			
- Função para inicializar a finger table com os mesmos valores para todos
  
- Os valores da fingertable vão ser atualizados na stabilize() com a lógica do fix_finger()
- #### ***Nota:*** ID pode ser o ID do próprio nó e o Addr é o Addr do próprio nó


    