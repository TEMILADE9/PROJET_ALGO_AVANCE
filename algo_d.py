import re
import getpass
import psycopg2
import psycopg2.extras
from datetime import date


def etablir_connexion():
    serveur = input("Nom ou adresse du serveur [127.0.0.1] : ").strip() or "127.0.0.1"
    port = input("Port [5432] : ").strip() or "5432"
    base = input("Nom de la base [commandes] : ").strip() or "commandes"
    utilisateur = input("Utilisateur [rodolphe] : ").strip() or "rodolphe"
    mot_passe = getpass.getpass("Mot de passe : ")

    try:
        connexion = psycopg2.connect(
            host=serveur,
            port=port,
            dbname=base,
            user=utilisateur,
            password=mot_passe,
        )
        print("Connexion etablie avec succes.")
        return connexion
    except psycopg2.OperationalError as erreur:
        print("Erreur de connexion :", erreur)
        return None


def ouvrir_base(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS DELEGUE (
            codedeleg VARCHAR(10) PRIMARY KEY, nomdeleg VARCHAR(50) NOT NULL,
            prenomdeleg VARCHAR(50), telephone VARCHAR(8), salaire NUMERIC
        );
        CREATE TABLE IF NOT EXISTS CLIENT (
            codcli VARCHAR(10) PRIMARY KEY, nomcli VARCHAR(50) NOT NULL,
            prenomcli VARCHAR(50), sexecli CHAR(1), telcli VARCHAR(8), villecli VARCHAR(50)
        );
        CREATE TABLE IF NOT EXISTS PRODUIT (
            refprod VARCHAR(10) PRIMARY KEY, libprod VARCHAR(50) NOT NULL, prixunit NUMERIC NOT NULL
        );
        CREATE TABLE IF NOT EXISTS COMMANDE (
            numcde VARCHAR(10) PRIMARY KEY, datecde DATE NOT NULL,
            codcli VARCHAR(10) NOT NULL REFERENCES CLIENT(codcli),
            codedeleg VARCHAR(10) NOT NULL REFERENCES DELEGUE(codedeleg)
        );
        CREATE TABLE IF NOT EXISTS COMMANDER (
            numcde VARCHAR(10) NOT NULL REFERENCES COMMANDE(numcde) ON DELETE CASCADE,
            refprod VARCHAR(10) NOT NULL REFERENCES PRODUIT(refprod),
            quantite INTEGER NOT NULL,
            PRIMARY KEY (numcde, refprod)
        );
        """)
    conn.commit()
    print("Base ouverte (tables pretes).")


def fermer_connexion(conn):
    conn.close()
    print("Connexion fermee.")


FORMAT_CODCLI    = r"^C\d{3}$"
FORMAT_NUMCDE    = r"^CDE\d{3}$"
FORMAT_REFPROD   = r"^P\d{3}$"
FORMAT_CODEDELEG = r"^D\d{3}$"


def saisir_code(libelle, pattern, exemple):
    while True:
        valeur = input(f"{libelle} (format : {exemple}) : ").strip().upper()
        if re.match(pattern, valeur):
            return valeur
        print(f"  -> Format invalide. Exemple attendu : {exemple}")


def saisir_texte_non_vide(libelle):
    while True:
        valeur = input(f"{libelle} : ").strip()
        if valeur != "":
            return valeur
        print("  -> Ce champ ne peut pas etre vide.")


def saisir_sexe():
    while True:
        valeur = input("Sexe (M/F) : ").strip().upper()
        if valeur in ("M", "F"):
            return valeur
        print("  -> Valeur invalide. Le sexe doit etre M ou F uniquement.")


def saisir_telephone():
    while True:
        valeur = input("Telephone (8 chiffres) : ").strip()
        if valeur.isdigit() and len(valeur) == 8:
            return valeur
        print("  -> Telephone invalide. Il doit contenir exactement 8 chiffres.")


def saisir_entier_positif(libelle):
    while True:
        valeur = input(f"{libelle} : ").strip()
        if valeur.isdigit() and int(valeur) > 0:
            return int(valeur)
        print(f"  -> {libelle} invalide. Ce doit etre un entier strictement positif.")


def existe(conn, table, colonne, valeur):
    with conn.cursor() as cur:
        cur.execute(f"SELECT 1 FROM {table} WHERE {colonne} = %s", (valeur,))
        return cur.fetchone() is not None


def ligne_existe(conn, numcde, refprod):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM COMMANDER WHERE numcde = %s AND refprod = %s",
            (numcde, refprod))
        return cur.fetchone() is not None


def enregistrer_client(conn, code, nom, prenom, sexe, tel, ville):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO CLIENT VALUES (%s,%s,%s,%s,%s,%s)",
                     (code, nom, prenom, sexe, tel, ville))
    conn.commit()


def enregistrer_commande(conn, numcde, codcli, codedeleg, datecde=None):
    if datecde is None:
        datecde = date.today()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO COMMANDE VALUES (%s,%s,%s,%s)",
                     (numcde, datecde, codcli, codedeleg))
    conn.commit()


def ajouter_produit_commande(conn, numcde, refprod, quantite):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO COMMANDER VALUES (%s,%s,%s)",
                     (numcde, refprod, quantite))
    conn.commit()


def consulter_commande(conn, numcde):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM COMMANDE WHERE numcde = %s", (numcde,))
        return cur.fetchone()


def lignes_commande(conn, numcde):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT p.refprod, p.libprod, p.prixunit, c.quantite,
                   (p.prixunit * c.quantite) AS sous_total
            FROM COMMANDER c JOIN PRODUIT p ON p.refprod = c.refprod
            WHERE c.numcde = %s
        """, (numcde,))
        return cur.fetchall()


def commandes_du_client(conn, codcli):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM COMMANDE WHERE codcli = %s ORDER BY datecde", (codcli,))
        return cur.fetchall()


def modifier_quantite(conn, numcde, refprod, nouvelle_quantite):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE COMMANDER SET quantite = %s WHERE numcde = %s AND refprod = %s",
            (nouvelle_quantite, numcde, refprod))
    conn.commit()


def supprimer_ligne(conn, numcde, refprod):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM COMMANDER WHERE numcde = %s AND refprod = %s",
            (numcde, refprod))
    conn.commit()


def calculer_montant(conn, numcde):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(p.prixunit * c.quantite), 0)
            FROM COMMANDER c JOIN PRODUIT p ON p.refprod = c.refprod
            WHERE c.numcde = %s
        """, (numcde,))
        return cur.fetchone()[0]


def afficher_commandes_client(conn, codcli):
    resultat = []
    for cde in commandes_du_client(conn, codcli):
        montant = calculer_montant(conn, cde["numcde"])
        resultat.append((cde["numcde"], cde["datecde"], montant))
    return resultat


def menu():
    conn = etablir_connexion()
    if conn is None:
        return
    ouvrir_base(conn)

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO DELEGUE VALUES ('D001','GBAGUIDI','Marc','97000000',150000)
            ON CONFLICT (codedeleg) DO NOTHING;
        """)
        cur.execute("""
            INSERT INTO PRODUIT VALUES ('P001','Clavier',8000)
            ON CONFLICT (refprod) DO NOTHING;
        """)
        cur.execute("""
            INSERT INTO PRODUIT VALUES ('P002','Souris',3500)
            ON CONFLICT (refprod) DO NOTHING;
        """)
    conn.commit()

    while True:
        print("\n--- GESTION DES COMMANDES (PostgreSQL) ---")
        print("1. Enregistrer un client")
        print("2. Enregistrer une commande")
        print("3. Ajouter un produit a une commande")
        print("4. Consulter une commande")
        print("5. Rechercher les commandes d'un client")
        print("6. Modifier une quantite commandee")
        print("7. Supprimer une ligne de commande")
        print("8. Calculer le montant d'une commande")
        print("9. Afficher toutes les commandes d'un client")
        print("0. Quitter")
        choix = input("Choix : ").strip()

        try:
            if choix == "1":
                code = saisir_code("Code client", FORMAT_CODCLI, "C001")
                if existe(conn, "CLIENT", "codcli", code):
                    print("  -> Ce code client existe deja.")
                    continue
                nom = saisir_texte_non_vide("Nom")
                prenom = saisir_texte_non_vide("Prenom")
                sexe = saisir_sexe()
                tel = saisir_telephone()
                ville = saisir_texte_non_vide("Ville")
                enregistrer_client(conn, code, nom, prenom, sexe, tel, ville)
                print("Client enregistre avec succes.")

            elif choix == "2":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                if existe(conn, "COMMANDE", "numcde", numcde):
                    print("  -> Ce numero de commande existe deja.")
                    continue
                codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
                if not existe(conn, "CLIENT", "codcli", codcli):
                    print("  -> Ce client n'existe pas.")
                    continue
                codedeleg = saisir_code("Code delegue", FORMAT_CODEDELEG, "D001")
                if not existe(conn, "DELEGUE", "codedeleg", codedeleg):
                    print("  -> Ce delegue n'existe pas.")
                    continue
                enregistrer_commande(conn, numcde, codcli, codedeleg)
                print("Commande enregistree avec succes.")

            elif choix == "3":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                if not existe(conn, "COMMANDE", "numcde", numcde):
                    print("  -> Cette commande n'existe pas.")
                    continue
                refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
                if not existe(conn, "PRODUIT", "refprod", refprod):
                    print("  -> Ce produit n'existe pas.")
                    continue
                quantite = saisir_entier_positif("Quantite")
                ajouter_produit_commande(conn, numcde, refprod, quantite)
                print("Produit ajoute a la commande.")

            elif choix == "4":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                cde = consulter_commande(conn, numcde)
                if cde:
                    print(dict(cde))
                    for ligne in lignes_commande(conn, numcde):
                        print("   ", dict(ligne))
                    print("   Montant total :", calculer_montant(conn, numcde))
                else:
                    print("Commande introuvable.")

            elif choix == "5":
                codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
                commandes = commandes_du_client(conn, codcli)
                if not commandes:
                    print("Aucune commande trouvee pour ce client.")
                for cde in commandes:
                    print(dict(cde))

            elif choix == "6":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
                if not ligne_existe(conn, numcde, refprod):
                    print("  -> Cette ligne de commande n'existe pas.")
                    continue
                quantite = saisir_entier_positif("Nouvelle quantite")
                modifier_quantite(conn, numcde, refprod, quantite)
                print("Quantite modifiee avec succes.")

            elif choix == "7":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
                if not ligne_existe(conn, numcde, refprod):
                    print("  -> Cette ligne de commande n'existe pas.")
                    continue
                reponse = input("Confirmer la suppression ? O/N : ").strip().upper()
                if reponse == "O":
                    supprimer_ligne(conn, numcde, refprod)
                    print("Ligne supprimee avec succes.")
                else:
                    print("Suppression annulee.")

            elif choix == "8":
                numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
                if not existe(conn, "COMMANDE", "numcde", numcde):
                    print("  -> Cette commande n'existe pas.")
                    continue
                print("Montant total :", calculer_montant(conn, numcde), "francs")

            elif choix == "9":
                codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
                resultat = afficher_commandes_client(conn, codcli)
                if not resultat:
                    print("Aucune commande trouvee pour ce client.")
                for numcde, datecde, montant in resultat:
                    print(f"Commande {numcde} | {datecde} | Montant: {montant}")

            elif choix == "0":
                fermer_connexion(conn)
                print("Au revoir.")
                break

            else:
                print("Choix invalide.")

        except psycopg2.Error as erreur:
            print("Erreur base de donnees :", erreur)
            conn.rollback()


if __name__ == "__main__":
    menu()
