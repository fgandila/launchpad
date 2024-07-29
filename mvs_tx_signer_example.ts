import { Transaction } from "@multiversx/sdk-core";
import { TransactionComputer, Address } from "@multiversx/sdk-core";
import { UserSigner, UserVerifier } from "@multiversx/sdk-wallet";
import { promises } from "fs";

const tx = new Transaction({
    "receiver": "erd1qqqqqqqqqqqqqpgq3y7ap48f5upyjp4zur0rjatvf8ejmrh4zeusqfnucz",
    "sender": "erd1e6yyv6v76pg52akzpmy2cps76kn749clyj83szxwh52j8kan3clsr0za68",
    "value": 0,
    "gasPrice": 1000000000n,
    "gasLimit": 50066500n,
    "chainID": "D",
    "version": 1,
    "data": Buffer.from("deployGuild"),
});

tx.nonce = 7n;

const fileContent = await promises.readFile("/Users/liviumarianberciu/DocumentsLocal/MultiversXProjects/test_wallet.json", { encoding: "utf8" });

const walletObject = JSON.parse(fileContent);
const signer = UserSigner.fromWallet(walletObject, "Liviu1234@");

const computer = new TransactionComputer();
const serializedTx = computer.computeBytesForSigning(tx);

tx.signature = await signer.sign(serializedTx);
console.log(Buffer.from(tx.signature).toString("hex"));

const verifier = UserVerifier.fromAddress(new Address("erd1e6yyv6v76pg52akzpmy2cps76kn749clyj83szxwh52j8kan3clsr0za68"));


const serializedTransaction = computer.computeBytesForVerifying(tx);

verifier.verify(serializedTransaction, tx.signature);

