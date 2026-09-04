import { Component, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule } from '@angular/common';
import { isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Router } from '@angular/router';
import { ChecklistSessionStore } from '../checklist-session.store';

type ChecklistItem = { key: string; label: string };
type ChecklistValue = boolean | null;

@Component({
  selector: 'app-formulario',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, HttpClientModule],
  templateUrl: './formulario.html',
  styleUrls: ['./formulario.css']
})
export class Formulario {
  form: FormGroup;
  submitted = false;
  loading = false;
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  private readonly apiUrl = '/api/checklist/submit';

  items: ChecklistItem[] = [
    /*
    { key: 'faroisBaixos', label: 'Faróis baixos' },
    { key: 'faroisAltos', label: 'Faróis altos' },
    { key: 'setasDianteirasLE', label: 'Setas dianteirasLE' },
    { key: 'setasDianteirasLD', label: 'Setas dianteirasLD' },
    { key: 'setasTraseirasLE', label: 'Setas traseirasLE' },
    { key: 'setasTraseirasLD', label: 'Setas traseiras LD' },

    { key: 'piscaAlerta', label: 'Pisca-alerta' },
    { key: 'lanternasDianteiras', label: 'Lanternas dianteiras' },
    { key: 'lanternasTraseiras', label: 'Lanternas traseiras' },
    { key: 'luzesFreio', label: 'Luzes de freio' },
    { key: 'luzRe', label: 'Luzes de ré' },
    { key: 'luzPlaca', label: 'Luz da placa' },
    { key: 'faroisNeblina', label: 'Faróis de neblina, quando aplicável' },
    { key: 'limpadoresParabrisa', label: 'Limpadores de para-brisa' },
    { key: 'palhetasParabrisa', label: 'Palhetas do para-brisa' },
    { key: 'esguichosParabrisa', label: 'Esguichos do para-brisa' },
    { key: 'reservatorioLimpador', label: 'Reservatório de água do limpador' },
    { key: 'parabrisaTrincas', label: 'Para-brisa sem trincas ou danos' },
    { key: 'espelhosRetrovisores', label: 'Espelhos retrovisores' },
    { key: 'carroceriaDanos', label: 'Carroceria sem danos aparentes' },*/
    {key: 'bafometro',label: 'Aplicar bafômetro e atento'},
    {key: 'inserirDiscoTCO', label:'Inserir disco TCO'},
    {key:'quadroDeTarifa', label:'Quadro de tarifa'},
    {key:'crlv', label:'CRLV'},
    {key:'discoFita', label:'Disco reserva ou fita'},
    {key:'apolice', label:'apolice RCO'},
    {key:'tco', label:'certificado TCO'},
    
    
    {key:'agerba', label:'AGERBA'},
    {key: 'adesivosANTT', label:'Adesivos(ANTT)'},
    {key: 'adesivosSAC', label:'Adesivos(SAC)'},
    {key: 'adesivosSaída', label:'Adesivos(saídas de emergência)'},
    {key: 'MarteloEmergencia', label:'Martelo de emergência'},
    {key: 'ledEmergencia', label:'LED de emergência'},
    {key: 'extintor', label:'Extintor de incêndio'},
    {key:'limpezaInterna', label:'Limpeza interna'},
    {key:'cortinas', label:'Cortinas'},
    {key:'papelHigienco', label: 'Papel Higiênico'},
    {key:'LimpezaDeBanheiro', label:'Limpeza de banheiro'},
    {key:'funcionamentoDeDescarga', label:'Funcionamento de descarga'},
    {key:'funcionamentoDePia', label:'Funcionamento de pia'},
    {key:'lixeiraDoBanheiro', label:'Lixeira do banheiro'},
    {key:'molaDoAssentoSanitário', label:'Mola do assento sanitário'},
    {key:'limpezaDoSanitario', label:'Limpeza do assento sanitário'},
    {key:'servicoDeBordo(água)', label:'Serviço de bordo(Água)'},
    {key:'servicoDeBordo(manta)',label:'Serviço de bordo'},
    {key:'itinerario', label:'Funcionamento do painel de itinerário'},
    {key:'abastecimento', label:'Abastecimento do véiculo'}
  
  ];

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private router: Router,
    public sessionStore: ChecklistSessionStore
  ) {
    const controls: Record<string, ChecklistValue> = {};
    this.items.forEach((item) => (controls[item.key] = null));
    this.form = this.fb.group(controls);

    if (!this.sessionStore.getSession() && this.isBrowser) {
      this.showAlert('Inicie informando nome do operador e prefixo do carro.');
      this.router.navigate(['/inicio']);
    }
  }

  isChecked(key: string, option: boolean): boolean {
    return this.form.get(key)?.value === option;
  }

  onToggle(key: string, option: boolean): void {
    const current = this.form.get(key)?.value as ChecklistValue;
    this.form.get(key)?.setValue(current === option ? null : option);
  }

  private allAnswered(): boolean {
    return this.items.every((item) => this.form.get(item.key)?.value !== null);
  }

  onSubmit(event?: Event): void {
    event?.preventDefault();
    this.submitted = true;

    if (!this.allAnswered()) {
      this.showAlert('Preencha todos os itens com V ou F antes de enviar.');
      return;
    }

    const session = this.sessionStore.getSession();
    if (!session) {
      this.showAlert('Sessão não encontrada. Recomece o checklist.');
      this.router.navigate(['/inicio']);
      return;
    }

    const confirmed = this.askConfirmation(
      `Eu, ${session.operatorName}, confirmo a veracidade do checklist do carro ${session.carPrefix}.`
    );

    if (!confirmed) {
      return;
    }

    const checklist = this.form.value as Record<string, boolean>;

    this.loading = true;
    this.http
      .post(this.apiUrl, {
        sessionId: session.sessionId,
        operatorName: session.operatorName,
        carPrefix: session.carPrefix,
        checklist
      })
      .subscribe({
        next: () => {
          this.loading = false;
          this.showAlert('Checklist enviado com sucesso!');
          this.sessionStore.clearSession();
          this.router.navigate(['/inicio']);
        },
        error: (err) => {
          this.loading = false;
          console.error(err);
          this.showAlert('Erro ao enviar checklist para o backend.');
        }
      });
  }

  private showAlert(message: string): void {
    if (this.isBrowser) {
      alert(message);
    }
  }

  private askConfirmation(message: string): boolean {
    return this.isBrowser ? confirm(message) : false;
  }
}
