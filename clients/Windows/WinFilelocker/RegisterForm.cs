using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace WinFilelocker
{
    public partial class RegisterForm : Form
    {
        public RegisterForm()
        {
            InitializeComponent();
        }

        private void txtCLIKey_TextChanged(object sender, EventArgs e)
        {

        }

        private void txtUserName_TextChanged(object sender, EventArgs e)
        {

        }

        private void label2_Click(object sender, EventArgs e)
        {

        }

        private void txtFilelockerServer_TextChanged(object sender, EventArgs e)
        {

        }

        private void label1_Click(object sender, EventArgs e)
        {

        }

        private void btnRegister_Click(object sender, EventArgs e)
        {
            string responseText = "";
            Dictionary<string, Object> response = Program.register(txtUserName.Text, txtPassword.Text, txtFilelockerServer.Text);
            foreach (string message in (List<string>)response["sMessages"])
            {
                responseText += message + "\n";
            }
            foreach (string message in (List<string>)response["fMessages"])
            {
                responseText += message + "\n";
            }
            if (((List<string>)response["fMessages"]).Count > 0)
            {
                lblResponse.Text = responseText;
            }
            else
            {
                Application.Run(new FilelockerTray(responseText));
            }
        }

        private void btnClose_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void RegisterForm_Load(object sender, EventArgs e)
        {

        }       
    }

}
