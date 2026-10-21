import { openDatabase, provisionAdmin } from './store.mjs';
import { resolve } from 'node:path';
// Read once from a secret environment variable; never log or commit the password.
const password=process.env.REZZKO_ADMIN_PASSWORD;
if(!password){console.error('REZZKO_ADMIN_PASSWORD fehlt. Als geheime Umgebungsvariable bereitstellen.');process.exit(1);}
const db=openDatabase(process.env.DATABASE_PATH||resolve('data/community.sqlite'));
try{await provisionAdmin(db,password);console.log('Admin-Konto Rezzko angelegt. Geheimnis anschließend aus der Umgebung entfernen.');}catch(e){console.error(e.message);process.exitCode=1;}finally{db.close();}
