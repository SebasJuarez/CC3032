from .instructions import AssemblySection

class MIPSEmitter:
    def __init__(self) -> None:
        self.text = AssemblySection('text')
        self.data = AssemblySection('data')
        self.externals = []  # nombres de rutinas externas simuladas
        self._string_labels = {}  # valor -> etiqueta

    def add_runtime(self) -> None:
        # Rutina simple para print integer usando syscall
        self.text.label('__print_int', 'runtime print integer')
        self.text.instr('li', '$v0', '1')
        self.text.instr('syscall')
        # imprimir newline (char code 10)
        self.text.instr('li', '$v0', '11')
        self.text.instr('li', '$a0', '10')
        self.text.instr('syscall')
        self.text.instr('jr', '$ra')
        # Rutina para imprimir string (usa $a0 como dirección)
        self.text.label('__print_str', 'runtime print string')
        self.text.instr('li', '$v0', '4')
        self.text.instr('syscall')
        # newline
        self.text.instr('li', '$v0', '11')
        self.text.instr('li', '$a0', '10')
        self.text.instr('syscall')
        self.text.instr('jr', '$ra')
        # Stubs para funciones externas llamadas (si no están definidas)
        for name in self.externals:
            self.text.label(name, 'external stub')
            # Devolver 0 en $v0 y retornar
            self.text.instr('move', '$v0', '$zero')
            self.text.instr('jr', '$ra')

    def to_string(self) -> str:
        parts = [self.data.to_text(), '', self.text.to_text()]
        return '\n'.join(parts)

    def add_string_literal(self, value: str) -> str:
        """Añade literal string a .data si no existe y devuelve etiqueta."""
        if value in self._string_labels:
            return self._string_labels[value]
        # Crear etiqueta única
        base = 'STR'
        idx = len(self._string_labels)
        label = f'{base}{idx}'
        # Limpiar comillas externas y escapar comillas internas
        inner = value[1:-1]
        # Reemplazar secuencias escapables simples (por ahora solo \n, \t)
        inner = inner.replace('\\n', '\n').replace('\\t', '\t')
        self.data.directive('asciiz', f'"{inner}"', comment=f'literal {idx}')
        self._string_labels[value] = label
        # Prepend label line (ensure label before directive)
        # Insert label object manually al final antes de la directiva agregada
        # Ajuste: reconstruir sección para poner label antes de última directiva
        last = self.data.items.pop()  # última directiva
        self.data.label(label)
        self.data.items.append(last)
        return label
