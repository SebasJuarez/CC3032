// OK-4-BREAK: Variante del test de control mostrando switch con break explicito

let x: integer = 5;
if (x < 0) {
    print("neg");
} else if (x == 0) {
    print("zero");
} else {
    print("pos");
}

let i: integer = 0; // ajusta este valor para probar distintos casos
// Variante con break: solo imprime el case coincidente (o default)
switch (i) {
    case 0: print("cero"); break;
    case 1: print("uno"); break;
    default: print("otro");
}
