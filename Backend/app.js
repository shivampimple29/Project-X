require("dotenv").config();

const express = require("express");
const app = express();

const port=process.env.PORT || 8000;

const mongoose=require("mongoose");
const DB_URL=process.env.ATLASDB_URL;
main()
  .then(() => {
    console.log("Connection with DB is successful!");
  })
  .catch((err) => {
    console.log(err);
  });

async function main() {
  await mongoose.connect(DB_URL);
}



app.listen(port, () => {
  console.log("App listening at port 8000");
});
