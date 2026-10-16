# PokerRoom API - Documentação

## Visão Geral

A classe `PokerRoom` é a interface principal para interagir com uma mesa de poker. Ela centraliza todas as informações da mesa e fornece acesso fácil através de propriedades e métodos.

## Inicialização

```python
from rooms.poker_room import PokerRoom

# Criar instância da sala
room = PokerRoom("SwC Poker - Logged in as jeffpk")

# Atualizar estado da mesa
room.update_table_state(snapshot=None)  # None usa imagem de exemplo
```

## Propriedades Principais

### Informações da Mesa

| Propriedade | Tipo | Descrição |
|------------|------|-----------|
| `room.hand_id` | `str` | ID da mão atual |
| `room.pot` | `str` | Valor do pot principal |
| `room.small_pot` | `str` | Valor do pot secundário |
| `room.dealer_position` | `int` | Posição do dealer (-1 se não detectado) |
| `room.community_cards` | `List[tuple]` | Cartas comunitárias [(rank, suit), ...] |

### Jogadores

| Propriedade | Tipo | Descrição |
|------------|------|-----------|
| `room.players` | `List[Player]` | Todos os jogadores na mesa |
| `room.active_players` | `List[Player]` | Jogadores ativos (presentes e com fichas) |
| `room.bb_positions` | `List[int]` | Posições dos big blinds |

### Configuração

| Propriedade | Tipo | Descrição |
|------------|------|-----------|
| `room.config` | `RoomConfig` | Configuração da sala |
| `room.room_name` | `str` | Nome da sala |

## Métodos Principais

### `update_table_state(snapshot=None)`

Atualiza o estado da mesa analisando um snapshot.

**Parâmetros:**
- `snapshot` (Optional[np.ndarray]): Imagem da mesa. Se None, usa imagem de exemplo.

**Retorna:**
- `TableInfo`: Informações completas da mesa

**Exemplo:**
```python
# Usar imagem de exemplo
room.update_table_state()

# Usar captura ao vivo
from core.window_handler import detect_window
snapshot = detect_window("SwC Poker - Logged in as jeffpk")
room.update_table_state(snapshot)
```

### `get_player_by_position(position)`

Retorna o jogador em uma posição específica.

**Parâmetros:**
- `position` (int): Posição do jogador (0-8)

**Retorna:**
- `Optional[Player]`: Jogador ou None se não encontrado

**Exemplo:**
```python
player = room.get_player_by_position(3)
if player:
    print(f"{player.name} - Stack: {player.stack}")
```

### `get_sb_player()`

Retorna o jogador no small blind.

**Retorna:**
- `Optional[Player]`: Jogador no SB ou None

**Exemplo:**
```python
sb = room.get_sb_player()
if sb:
    print(f"Small Blind: {sb.name}")
```

### `get_bb_player()`

Retorna o jogador no big blind.

**Retorna:**
- `Optional[Player]`: Jogador no BB ou None

**Exemplo:**
```python
bb = room.get_bb_player()
if bb:
    print(f"Big Blind: {bb.name}")
```

## Estrutura do Player

Cada jogador tem os seguintes atributos:

```python
@dataclass
class Player:
    name: str                    # Nome do jogador
    position: int                # Posição na mesa (0-8)
    pos_preflop: Position        # Posição pré-flop (SB, BB, etc)
    is_present: bool             # Se está presente na mesa
    is_active: bool              # Se está ativo na mão
    stack: float                 # Valor do stack
    current_bet: float           # Aposta atual
    just_joined: bool            # Se acabou de entrar
    pending_big_blind: bool      # Se tem BB pendente
```

## Exemplo Completo de Uso

```python
from rooms.poker_room import PokerRoom

# 1. Inicializar sala
room = PokerRoom("SwC Poker - Logged in as jeffpk")

# 2. Atualizar estado
room.update_table_state()

# 3. Acessar informações da mesa
print(f"Mão: {room.hand_id}")
print(f"Pot: {room.pot}")
print(f"Dealer: {room.dealer_position}")

# 4. Verificar cartas comunitárias
if room.community_cards:
    for rank, suit in room.community_cards:
        print(f"Carta: {rank}{suit}")

# 5. Analisar jogadores
for player in room.active_players:
    print(f"{player.name}: Stack={player.stack}, Bet={player.current_bet}")

# 6. Verificar blinds
sb = room.get_sb_player()
bb = room.get_bb_player()

if sb and bb:
    print(f"SB: {sb.name} | BB: {bb.name}")

# 7. Tomar decisões baseadas no estado
if len(room.community_cards) >= 3:  # Flop ou mais
    if len(room.active_players) <= 2:  # Heads-up
        print("Situação: Heads-up no flop")
```

## Implementando Estratégias

Para implementar estratégias, crie uma classe que recebe o `PokerRoom`:

```python
class MyStrategy:
    def __init__(self, room: PokerRoom):
        self.room = room
    
    def should_fold(self) -> bool:
        # Sua lógica aqui
        return False
    
    def should_call(self) -> bool:
        # Sua lógica aqui
        return True
    
    def should_raise(self) -> bool:
        # Sua lógica aqui
        return False
    
    def get_raise_amount(self) -> float:
        # Calcular valor do raise
        pot = float(self.room.pot.replace(',', '.'))
        return pot * 0.5

# Uso
room = PokerRoom("SwC Poker - Logged in as jeffpk")
room.update_table_state()

strategy = MyStrategy(room)
if strategy.should_raise():
    amount = strategy.get_raise_amount()
    print(f"Raise: {amount}")
```

## Salas Suportadas

- **SwC Poker**: `"SwC Poker - Logged in as jeffpk"`
- **Bodog Poker**: `"Bodog.com - Poker Lobby"`
- **ACR Poker**: `"Lobby ACR Poker Conectado como jeffersom"`

## Notas Importantes

1. **Sempre chame `update_table_state()`** antes de acessar as propriedades da mesa
2. **Verifique se os valores não são None** antes de usar
3. **Use `active_players`** em vez de `players` para filtrar apenas jogadores ativos
4. **Cartas comunitárias** estão no formato `[(rank, suit), ...]` onde:
   - `rank`: '2'-'9', 'T', 'J', 'Q', 'K', 'A'
   - `suit`: 'S' (Spades), 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs)

## Debugging

Para ativar o modo debug e ver as imagens de detecção:

```python
room = PokerRoom("SwC Poker - Logged in as jeffpk")
room.config.debug_mode = True
room.update_table_state()

# Imagem será salva em: debug_table_recognition.png
```
