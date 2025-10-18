// OK-2: Funciones, parámetros y recursividad
function fact(n: integer): integer {
    if (n <= 1) { return 1; }
    return n * fact(n - 1);
}

function suma(a: integer, b: integer): integer {
    return a + b;
}

let r1: integer = suma(3, 4);
let r2: integer = fact(5);
print(r1);
print(r2);
