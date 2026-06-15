class ChunkIEND:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.data = data
        self.crc = crc

    def __str__(self) -> str:
        return "IEND: end of PNG stream (empty data)"
